from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

import numpy as np

from surveillance.region import crop_to_region

log = logging.getLogger(__name__)


@dataclass
class FrameData:
    """A single frame ready for inference."""
    raw: np.ndarray
    cropped: np.ndarray


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


def collect_frames(
    stream,
    stop: threading.Event,
    count: int,
    interval: float,
    region: tuple[float, float, float, float] | None,
    first_raw: np.ndarray | None = None,
    first_cropped: np.ndarray | None = None,
) -> list[FrameData]:
    """Collect *count* frames from stream, starting with *first_raw* if given."""
    frames: list[FrameData] = []
    for i in range(count):
        if i == 0 and first_raw is not None:
            raw = first_raw
            crop = first_cropped if first_cropped is not None else raw
        else:
            fr = stream.read_frame()
            if fr is None:
                time.sleep(0.05)
                continue
            crop = crop_to_region(fr, region) if region else fr
            raw = fr
        frames.append(FrameData(raw=raw, cropped=crop))
        if i < count - 1:
            time.sleep(interval)

    if count > 1:
        log.debug("collect_frames: %d frames interval=%.2f", len(frames), interval)
    return frames


def pick_best_frame(frames: list[FrameData], scores: list[dict[str, float]]) -> np.ndarray:
    """Return the raw frame with highest max confidence score."""
    if not frames:
        raise ValueError("empty frames")
    best_idx = 0
    best_sc = max(scores[0].values()) if scores[0] else 0.0
    for i in range(1, len(frames)):
        sc = max(scores[i].values()) if scores[i] else 0.0
        if sc > best_sc:
            best_sc = sc
            best_idx = i
    return frames[best_idx].raw.copy()
