from __future__ import annotations

import argparse
import logging
import signal
import threading
import time
from pathlib import Path
from typing import Any

from surveillance.config_loader import camera_effective_config, load_config
from surveillance.motion import MotionConfig, MotionGate
from surveillance.stream import RTSPReader, StreamConfig
from surveillance.detectors.pipeline import AIPipeline, PipelineResult
from surveillance.hooks import HooksManager
from surveillance.recordings import RecordingManager
from surveillance.http_server import start_http_server
from surveillance.region import crop_to_region
from surveillance.vision_burst import (
    VisionBurstConfig,
    merge_pipeline_results,
    pick_best_snapshot_frame,
    sample_vision_burst,
)
from surveillance.onvif import OnvifUrlResolver, parse_onvif_url

log = logging.getLogger(__name__)


def _motion_cfg(eff: dict[str, Any]) -> MotionConfig:
    return MotionConfig.from_dict(eff.get("motion"))


def _ai_cooldown_sec(eff: dict[str, Any]) -> float:
    m = eff.get("motion") or {}
    return float(m.get("ai_cooldown_sec", 2.0))


def _recordings_mgr(eff: dict[str, Any], cam_id: str) -> RecordingManager:
    rc = eff.get("recordings")
    cfg = rc if isinstance(rc, dict) else {}
    base = str(cfg.get("base_dir", "data"))
    return RecordingManager(camera_id=cam_id, base_dir=base, recordings_cfg=cfg)


def _vision_burst_cfg(eff: dict[str, Any]) -> VisionBurstConfig:
    vb = eff.get("vision_burst")
    return VisionBurstConfig.from_dict(vb if isinstance(vb, dict) else None)


def _flat_vision_labels(result: PipelineResult) -> dict[str, float]:
    out: dict[str, float] = {}
    for vr in result.vision.values():
        for k, v in vr.labels.items():
            out[k] = float(v)
    return out


def camera_worker(
    full_cfg: dict[str, Any],
    camera_row: dict[str, Any],
    stop: threading.Event,
) -> None:
    eff = camera_effective_config(full_cfg, camera_row)
    cam_id = str(eff.get("id") or "camera")

    # stream_url 支持 rtsp:// 和 onvif:// 两种协议
    stream_url = str(eff.get("stream_url") or eff.get("rtsp_url") or "").strip()
    if not stream_url:
        log.error("相机 %s 未配置 stream_url，跳过", cam_id)
        return

    if stream_url.startswith("onvif://"):
        log.info("[%s] ONVIF 解析中: %s", cam_id, stream_url)
        try:
            onvif_cfg = parse_onvif_url(stream_url)
            resolver = OnvifUrlResolver(onvif_cfg)
            stream_url = resolver.resolve()
            resolver.close()
        except Exception:
            log.exception("[%s] ONVIF 解析失败，跳过", cam_id)
            return

    stream = RTSPReader(StreamConfig(rtsp_url=stream_url))
    motion_cfg = _motion_cfg(eff)
    motion = MotionGate(motion_cfg)
    check_iv = motion_cfg.check_interval_sec
    pipeline = AIPipeline.from_camera_detectors(eff.get("detectors"))
    rec_mgr = _recordings_mgr(eff, cam_id)
    hooks_mgr = HooksManager(eff.get("hooks"))
    ai_cd = _ai_cooldown_sec(eff)
    last_ai = 0.0

    log.info("线程启动: %s", cam_id)
    try:
        while not stop.is_set():
            stream.skip_frames(check_iv)
            frame = stream.read_frame()
            if frame is None:
                continue
            raw_frame = frame.copy()
            region = eff.get("region")
            if region:
                frame = crop_to_region(frame, region)
            moving, ratio = motion.is_motion(frame)
            if not moving:
                continue

            # 运动触发录制（独立于 AI，不受 AI/HA 冷却控制）
            m_cfg = rec_mgr.should_record("motion")
            if m_cfg is not None:
                ev_data = rec_mgr.fire("motion", m_cfg, raw_frame, stream, stop)
                if ev_data:
                    ev_data["camera_id"] = cam_id
                    hooks_mgr.fire("motion", ev_data)

            now = time.time()
            if now - last_ai < ai_cd:
                log.debug(
                    "[%s] motion ratio=%.5f 但 AI 冷却中 (%.2fs / %.2fs)",
                    cam_id,
                    ratio,
                    now - last_ai,
                    ai_cd,
                )
                continue
            last_ai = now
            log.debug("[%s] motion 触发 ratio=%.5f → 开始 detector", cam_id, ratio)

            if not pipeline.has_vision_detectors():
                log.debug("[%s] 无启用视觉检测器，跳过推理", cam_id)
                continue

            burst_cfg = _vision_burst_cfg(eff)
            if burst_cfg.enabled:
                log.debug(
                    "[%s] detector: vision_burst window=%.2fs interval=%.2fs",
                    cam_id,
                    burst_cfg.window_sec,
                    burst_cfg.interval_sec,
                )
                samples = sample_vision_burst(
                    stream, pipeline, cam_id, stop, burst_cfg, frame, region
                )
                if not samples:
                    log.debug("[%s] detector: burst 无采样帧", cam_id)
                    continue
                result = merge_pipeline_results([pr for _, pr in samples])
                snapshot_bgr = pick_best_snapshot_frame(samples)
                burst_meta = {
                    "enabled": True,
                    "frames": len(samples),
                    "window_sec": burst_cfg.window_sec,
                    "interval_sec": burst_cfg.interval_sec,
                }
            else:
                log.debug("[%s] detector: 单帧推理", cam_id)
                # 多帧 LLM：运动触发后继续采集数帧，间隔 >0.5 秒
                llm_extra = None
                llm_cfg = eff.get("detectors", {}).get("llm_vision", {})
                if isinstance(llm_cfg, dict) and llm_cfg.get("enabled") and int(llm_cfg.get("frames", 1)) > 1:
                    n = int(llm_cfg["frames"])
                    llm_extra = []
                    for _ in range(n - 1):
                        fr = stream.read_frame()
                        if fr is None:
                            time.sleep(0.05)
                            continue
                        llm_extra.append(fr)
                        if _ < n - 2:
                            time.sleep(max(0.5, motion_cfg.check_interval_sec))
                extra = {"llm_extra_frames": llm_extra} if llm_extra else None
                result = pipeline.run(frame, camera_id=cam_id, rtsp_url=None, extra=extra)
                snapshot_bgr = raw_frame.copy()
                burst_meta = {"enabled": False, "frames": 1}

            flat_labels = _flat_vision_labels(result)
            sig = result.significant(pipeline.label_thresholds)
            log.debug(
                "[%s] detector 完成 burst=%s frames=%s labels=%s significant=%s thresholds=%s",
                cam_id,
                burst_meta.get("enabled"),
                burst_meta.get("frames"),
                flat_labels,
                sig,
                pipeline.label_thresholds,
            )
            if not sig:
                continue

            # AI 检测录制：对每个显著标签按配置录制
            for label in sig:
                r_cfg = rec_mgr.should_record(label)
                if r_cfg is not None:
                    ev_data = rec_mgr.fire(label, r_cfg, snapshot_bgr, stream, stop)
                    if ev_data:
                        ev_data["camera_id"] = cam_id
                        ev_data["labels"] = flat_labels
                        hooks_mgr.fire(label, ev_data)

            log.info("[%s] 检测到显著目标: %s", cam_id, sig)
    finally:
        pipeline.close()
        stream.close()
        log.info("线程结束: %s", cam_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="多路 RTSP 运动触发 + YOLO 检测")

    parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="配置文件路径（默认当前目录 config.yaml）",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="DEBUG 日志（motion 触发、AI 冷却、detector 每帧/合并结果等）",
    )
    parser.add_argument(
        "--http",
        metavar="ADDR",
        default="",
        help="启动 HTTP 服务器，格式 :8080 或 0.0.0.0:8080",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s [%(threadName)s] %(name)s: %(message)s",
    )

    cfg_path = Path(args.config)
    raw = load_config(cfg_path)
    cameras = raw.get("cameras")
    if not isinstance(cameras, list) or not cameras:
        raise SystemExit("配置中 cameras 必须为非空列表")

    # 可选 HTTP 服务器（后台线程，不阻塞主流程）
    if args.http:
        cam_ids = [c.get("id", f"cam{i}") for i, c in enumerate(cameras) if c.get("enabled", True)]
        data_base = "data"
        rc = raw.get("defaults", {}).get("recordings") or {}
        if isinstance(rc, dict):
            data_base = str(rc.get("base_dir", "data"))
        start_http_server(cam_ids, data_base, args.http)

    stop = threading.Event()

    def handle_sig(*_: Any) -> None:
        log.info("收到退出信号，正在停止…")
        stop.set()

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    threads: list[threading.Thread] = []
    for cam in cameras:
        if not cam.get("enabled", True):
            log.info("跳过未启用相机: %s", cam.get("id"))
            continue
        t = threading.Thread(
            target=camera_worker,
            name=f"cam-{cam.get('id', '?')}",
            args=(raw, cam, stop),
            daemon=False,
        )
        threads.append(t)
        t.start()

    if not threads:
        raise SystemExit("没有启用的相机")

    try:
        while not stop.is_set():
            if not any(t.is_alive() for t in threads):
                break
            time.sleep(0.3)
    except KeyboardInterrupt:
        stop.set()
    finally:
        stop.set()
        for t in threads:
            t.join(timeout=30.0)


if __name__ == "__main__":
    main()
