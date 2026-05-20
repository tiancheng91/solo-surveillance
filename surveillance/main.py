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
from surveillance.recordings import RecordingManager
from surveillance.notifiers import Notifier
from surveillance.notifiers.hass import HassNotifier
from surveillance.notifiers.hooks import HooksNotifier
from surveillance.http_server import start_http_server
from surveillance.region import crop_to_region
from surveillance.vision_burst import collect_frames
from surveillance.onvif import OnvifUrlResolver, parse_onvif_url

log = logging.getLogger(__name__)


def _motion_cfg(eff: dict[str, Any]) -> MotionConfig:
    return MotionConfig.from_dict(eff.get("motion"))


def _ai_cooldown_sec(eff: dict[str, Any]) -> float:
    ai = eff.get("ai") or {}
    return float(ai.get("cooldown_sec", 10.0))


def _ai_frame_count(eff: dict[str, Any]) -> int:
    ai = eff.get("ai") or {}
    return int(ai.get("frames", 1))


def _ai_frame_interval(eff: dict[str, Any]) -> float:
    ai = eff.get("ai") or {}
    return float(ai.get("interval_sec", 0.5))


def _recordings_mgr(eff: dict[str, Any], cam_id: str) -> RecordingManager:
    rc = eff.get("recordings")
    cfg = rc if isinstance(rc, dict) else {}
    base = str(cfg.get("base_dir", "data"))
    return RecordingManager(camera_id=cam_id, base_dir=base, recordings_cfg=cfg)


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
    notifiers: list[Notifier] | None = None,
) -> None:
    eff = camera_effective_config(full_cfg, camera_row)
    cam_id = str(eff.get("id") or "camera")

    # stream_url 支持 rtsp:// 和 onvif:// 两种协议
    stream_url = str(eff.get("stream_url") or "").strip()
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
    pipeline = AIPipeline.from_camera_detectors(eff.get("detectors"), full_cfg.get("llm"))
    rec_mgr = _recordings_mgr(eff, cam_id)
    ai_cd = _ai_cooldown_sec(eff)
    last_ai = 0.0

    log.info("线程启动: %s", cam_id)
    try:
        while not stop.is_set():
            stream.skip_frames(check_iv, stop)
            frame = stream.read_frame(stop)
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
                    for n in (notifiers or []):
                        n.fire("motion", ev_data)

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

            # 采集帧 → 批量推理（统一路径，不再区分 burst / 单帧）
            ai_count = _ai_frame_count(eff)
            ai_interval = _ai_frame_interval(eff)
            ai_frames = collect_frames(stream, stop, ai_count, ai_interval, region, raw_frame, frame)
            if not ai_frames:
                log.debug("[%s] 未采集到帧，跳过", cam_id)
                continue

            cropped_frames = [f.cropped for f in ai_frames]
            result = pipeline.run_batch(cropped_frames, camera_id=cam_id, rtsp_url=None)
            snapshot_bgr = ai_frames[0].raw.copy()

            flat_labels = _flat_vision_labels(result)
            sig = result.significant(pipeline.label_thresholds)
            log.debug(
                "[%s] AI 完成 frames=%d labels=%s significant=%s thresholds=%s",
                cam_id,
                len(ai_frames),
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
                        for n in (notifiers or []):
                            n.fire(label, ev_data)

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
        action="count",
        default=0,
        help="-v 应用自身 DEBUG；-vv 包含库（httpx/openai）DEBUG 日志",
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
        force=True,
    )
    if args.verbose < 2:
        for lib in ("httpx", "httpcore", "openai", "urllib3"):
            logging.getLogger(lib).setLevel(logging.WARNING)

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

    notifiers: list[Notifier] = []
    for cls in (HassNotifier, HooksNotifier):
        n = cls.from_config(raw)
        if n:
            notifiers.append(n)

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
            kwargs={"notifiers": notifiers},
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
