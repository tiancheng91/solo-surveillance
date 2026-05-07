from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Tuple

import cv2
import numpy as np

log = logging.getLogger(__name__)


@dataclass
class MotionConfig:
    resize_width: int = 320
    blur_ksize: int = 5
    diff_threshold: int = 28
    min_change_ratio: float = 0.012

    @classmethod
    def from_dict(cls, d: dict | None) -> MotionConfig:
        if not d:
            return cls()
        return cls(
            resize_width=int(d.get("resize_width", 320)),
            blur_ksize=int(d.get("blur_ksize", 5)),
            diff_threshold=int(d.get("diff_threshold", 28)),
            min_change_ratio=float(d.get("min_change_ratio", 0.012)),
        )


class MotionGate:
    """帧差判断画面是否变化，供 AI 门控。"""

    def __init__(self, cfg: MotionConfig) -> None:
        self._cfg = cfg
        self._prev: np.ndarray | None = None

    def reset(self) -> None:
        self._prev = None

    def is_motion(self, frame_bgr: np.ndarray) -> Tuple[bool, float]:
        h, w = frame_bgr.shape[:2]
        if w > self._cfg.resize_width and self._cfg.resize_width > 0:
            scale = self._cfg.resize_width / float(w)
            small = cv2.resize(frame_bgr, (int(w * scale), int(h * scale)))
        else:
            small = frame_bgr

        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        k = max(1, self._cfg.blur_ksize | 1)
        gray = cv2.GaussianBlur(gray, (k, k), 0)

        if self._prev is None or self._prev.shape != gray.shape:
            self._prev = gray.copy()
            return False, 0.0

        diff = cv2.absdiff(self._prev, gray)
        self._prev = gray.copy()

        _, th = cv2.threshold(diff, self._cfg.diff_threshold, 255, cv2.THRESH_BINARY)
        ratio = float((th > 0).sum()) / float(th.size) if th.size else 0.0
        return ratio >= self._cfg.min_change_ratio, ratio
