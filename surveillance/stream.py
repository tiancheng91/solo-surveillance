from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass

import cv2
import numpy as np

log = logging.getLogger(__name__)


@dataclass
class StreamConfig:
    rtsp_url: str
    open_timeout_ms: int = 8000
    read_timeout_ms: int = 5000
    reconnect_delay_sec: float = 3.0


class RTSPReader:
    """带超时与重连的 RTSP 读帧。"""

    def __init__(self, cfg: StreamConfig) -> None:
        self._cfg = cfg
        self._cap: cv2.VideoCapture | None = None

    def _apply_env(self) -> None:
        # OpenCV 4.x：TCP 更稳
        os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")

    def _open(self) -> bool:
        self.close()
        self._apply_env()
        cap = cv2.VideoCapture(self._cfg.rtsp_url, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            log.warning("无法打开 RTSP: %s", self._cfg.rtsp_url)
            return False
        for prop, val in (
            (cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, float(self._cfg.open_timeout_ms)),
            (cv2.CAP_PROP_READ_TIMEOUT_MSEC, float(self._cfg.read_timeout_ms)),
        ):
            try:
                cap.set(prop, val)
            except Exception:
                pass
        self._cap = cap
        log.info("已连接 RTSP")
        return True

    def close(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                log.exception("释放 VideoCapture")
            self._cap = None

    def read_frame(self, stop: threading.Event | None = None) -> np.ndarray | None:
        while True:
            if stop and stop.is_set():
                return None
            if self._cap is None or not self._cap.isOpened():
                if not self._open():
                    self._sleep_or_stop(self._cfg.reconnect_delay_sec, stop)
                    continue
            assert self._cap is not None
            ok, frame = self._cap.read()
            if not ok or frame is None or frame.size == 0:
                log.warning("读帧失败，准备重连")
                self.close()
                self._sleep_or_stop(self._cfg.reconnect_delay_sec, stop)
                continue
            return frame

    def skip_frames(self, duration_sec: float, stop: threading.Event | None = None) -> None:
        """Pause frame consumption for *duration_sec*.

        Lets the RTSP buffer absorb frames naturally — no FFMPEG decode cost during the pause.
        After waking up, discards a few undecoded frames to avoid HEVC decoder warnings
        when the first buffered packet references an already-evicted keyframe.
        """
        if duration_sec <= 0:
            return
        if stop:
            # 分片睡眠，允许提前退出
            deadline = time.time() + duration_sec
            while time.time() < deadline:
                if stop.is_set():
                    return
                time.sleep(min(0.1, deadline - time.time()))
        else:
            time.sleep(duration_sec)
        # Drain the internal buffer so the next read_frame() starts on a fresh
        # keyframe, avoiding "Could not find ref with POC" HEVC warnings.
        self._drain()

    @staticmethod
    def _sleep_or_stop(duration: float, stop: threading.Event | None) -> None:
        if not stop:
            time.sleep(duration)
            return
        deadline = time.time() + duration
        while time.time() < deadline:
            if stop.is_set():
                return
            time.sleep(min(0.1, deadline - time.time()))

    def _drain(self) -> None:
        if self._cap is None or not self._cap.isOpened():
            return
        for _ in range(10):
            if not self._cap.grab():
                break
