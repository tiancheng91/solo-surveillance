from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

import numpy as np

from surveillance.detectors.base import VisionResult
from surveillance.detectors.pipeline import AIPipeline, PipelineResult
from surveillance.region import crop_to_region

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class VisionBurstConfig:
    enabled: bool = False
    window_sec: float = 1.2
    interval_sec: float = 0.3

    @classmethod
    def from_dict(cls, d: dict | None) -> VisionBurstConfig:
        if not d:
            return cls(enabled=False)
        win = float(d.get("window_sec", 1.2))
        iv = float(d.get("interval_sec", 0.3))
        min_iv = 0.2
        if win <= 0:
            win = 1.2
        iv = max(min_iv, iv)
        return cls(
            enabled=bool(d.get("enabled", False)),
            window_sec=win,
            interval_sec=iv,
        )


def merge_pipeline_results(results: list[PipelineResult]) -> PipelineResult:
    """多帧结果按检测器名合并标签（同一 key 取最大置信度）。"""
    acc: dict[str, dict[str, float]] = {}
    order: list[str] = []
    n = len(results)
    for pr in results:
        for name, vr in pr.vision.items():
            if name not in acc:
                acc[name] = dict(vr.labels)
                order.append(name)
            else:
                for k, v in vr.labels.items():
                    acc[name][k] = max(float(acc[name].get(k, 0.0)), float(v))
    vision = {
        name: VisionResult(
            labels=acc[name],
            raw={"burst_merged": True, "burst_frames": n},
        )
        for name in order
    }
    return PipelineResult(vision=vision, audio={})


def _frame_score(pr: PipelineResult) -> float:
    s = 0.0
    for vr in pr.vision.values():
        if vr.labels:
            s = max(s, max(float(x) for x in vr.labels.values()))
    return s


def pick_best_snapshot_frame(samples: list[tuple[np.ndarray, PipelineResult]]) -> np.ndarray:
    """选置信度最高的一帧用于截图（BGR）。"""
    if not samples:
        raise ValueError("empty burst")
    best_fr = samples[0][0]
    best_sc = _frame_score(samples[0][1])
    for fr, pr in samples[1:]:
        sc = _frame_score(pr)
        if sc > best_sc:
            best_sc = sc
            best_fr = fr
    return best_fr.copy()


def sample_vision_burst(
    stream,
    pipeline: AIPipeline,
    camera_id: str,
    stop: threading.Event,
    cfg: VisionBurstConfig,
    first_frame: np.ndarray,
    region=None,
) -> list[tuple[np.ndarray, PipelineResult]]:
    """
    在 [t0, t0+window_sec] 内按 interval 采样：首帧用 first_frame，其后 read_frame。
    """
    samples: list[tuple[np.ndarray, PipelineResult]] = []
    t0 = time.monotonic()
    end = t0 + cfg.window_sec

    infer_frame = crop_to_region(first_frame, region)
    r0 = pipeline.run(infer_frame, camera_id=camera_id, rtsp_url=None)
    samples.append((first_frame.copy(), r0))

    next_t = t0 + cfg.interval_sec
    while next_t <= end + 1e-9:
        if stop.is_set():
            break
        while True:
            if stop.is_set():
                return samples
            rem = next_t - time.monotonic()
            if rem <= 0:
                break
            time.sleep(min(0.05, rem))

        fr = stream.read_frame()
        if fr is None:
            continue
        infer_fr = crop_to_region(fr, region)
        r = pipeline.run(infer_fr, camera_id=camera_id, rtsp_url=None, skip={"llm_vision"})
        samples.append((fr.copy(), r))
        next_t += cfg.interval_sec

    log.debug("vision_burst: %s 帧 window=%.2fs interval=%.2fs", len(samples), cfg.window_sec, cfg.interval_sec)
    return samples
