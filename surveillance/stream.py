from __future__ import annotations

import logging
import os
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

    def read_frame(self) -> np.ndarray | None:
        while True:
            if self._cap is None or not self._cap.isOpened():
                if not self._open():
                    time.sleep(self._cfg.reconnect_delay_sec)
                    continue
            assert self._cap is not None
            ok, frame = self._cap.read()
            if not ok or frame is None or frame.size == 0:
                log.warning("读帧失败，准备重连")
                self.close()
                time.sleep(self._cfg.reconnect_delay_sec)
                continue
            return frame

    def skip_frames(self, duration_sec: float) -> None:
        """Pause frame consumption for *duration_sec*.

        Lets the RTSP buffer absorb frames naturally — no FFMPEG decode cost during the pause.
        """
        if duration_sec <= 0:
            return
        time.sleep(duration_sec)
