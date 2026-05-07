from __future__ import annotations

import csv
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from surveillance.stream import RTSPReader

log = logging.getLogger(__name__)

_DATE_FMT = "%Y-%m-%d"
_TS_FMT = "%H%M%S"
_CSV_HEADER = ["start_time", "end_time", "event_type", "snapshot_path", "clip_path"]


@dataclass
class RecordingConfig:
    """单个事件类型（motion / person / …）的录制选项。"""
    snapshot: bool = False
    clip: bool = False
    clip_seconds: float = 5.0

    @classmethod
    def from_dict(cls, d: dict | None) -> RecordingConfig:
        if not d:
            return cls()
        return cls(
            snapshot=bool(d.get("snapshot", False)),
            clip=bool(d.get("clip", False)),
            clip_seconds=float(d.get("clip_seconds", 5.0)),
        )


class RecordingManager:
    """每路相机独立持有：按事件类型录制截图/视频，维护 timeline.csv。"""

    def __init__(
        self,
        camera_id: str,
        base_dir: str = "data",
        recordings_cfg: dict | None = None,
    ) -> None:
        self._camera_id = camera_id
        self._base_dir = Path(base_dir)
        self._configs: dict[str, RecordingConfig] = {}
        self._last_event_time: dict[str, float] = {}  # event_type -> timestamp

        rc = recordings_cfg or {}
        for key, val in rc.items():
            if isinstance(val, dict) and key != "base_dir":
                self._configs[key] = RecordingConfig.from_dict(val)

        log.debug(
            "RecordingManager[%s] base=%s configs=%s",
            camera_id, base_dir, list(self._configs.keys()),
        )

    # ── public API ──────────────────────────────────────────────

    _DEDUP_SECONDS = 3.0

    def should_record(self, event_type: str) -> RecordingConfig | None:
        """返回匹配的 RecordingConfig，None 表示该事件类型未配置或不录制。"""
        cfg = self._configs.get(event_type)
        if cfg is None:
            return None
        if not cfg.snapshot and not cfg.clip:
            return None
        return cfg

    def fire(
        self,
        event_type: str,
        cfg: RecordingConfig,
        frame_bgr: np.ndarray,
        stream: RTSPReader,
        stop: threading.Event,
    ) -> dict | None:
        """按配置执行录制并写 timeline（含同类型防重）。返回事件元数据或 None（防重跳过）。"""
        now_ts = time.time()
        last = self._last_event_time.get(event_type, 0.0)
        if now_ts - last < self._DEDUP_SECONDS:
            log.debug("[%s] %s 录制防重跳过", self._camera_id, event_type)
            return None
        self._last_event_time[event_type] = now_ts

        now = datetime.now()
        date_str = now.strftime(_DATE_FMT)
        ts_str = now.strftime(_TS_FMT)

        date_dir = self._base_dir / self._camera_id / date_str
        snap_dir = date_dir / "snapshots"
        clip_dir = date_dir / "clips"

        snap_path_rel: str | None = None
        clip_path_rel: str | None = None

        start_iso = now.isoformat()

        if cfg.snapshot:
            snap_dir.mkdir(parents=True, exist_ok=True)
            snap_file = snap_dir / f"{ts_str}_{event_type}.jpg"
            ok = cv2.imwrite(
                str(snap_file),
                frame_bgr,
                [int(cv2.IMWRITE_JPEG_QUALITY), 92],
            )
            if ok:
                snap_path_rel = str(snap_file.relative_to(date_dir))
                log.info("[%s] 截图已保存: %s", self._camera_id, snap_file)
            else:
                log.warning("[%s] 截图保存失败: %s", self._camera_id, snap_file)

        if cfg.clip:
            clip_dir.mkdir(parents=True, exist_ok=True)
            clip_file = clip_dir / f"{ts_str}_{event_type}.mp4"
            self._record_clip(stream, clip_file, cfg.clip_seconds, frame_bgr, stop)
            if clip_file.exists() and clip_file.stat().st_size > 0:
                clip_path_rel = str(clip_file.relative_to(date_dir))
                log.info("[%s] 视频已保存: %s", self._camera_id, clip_file)
            else:
                log.warning("[%s] 视频保存失败或为空: %s", self._camera_id, clip_file)

        end_iso = datetime.now().isoformat()
        self._append_timeline(date_dir, start_iso, end_iso, event_type, snap_path_rel, clip_path_rel)

        return {
            "event_type": event_type,
            "start_time": start_iso,
            "end_time": end_iso,
            "snapshot_path": snap_path_rel,
            "clip_path": clip_path_rel,
        }

    # ── 内部方法 ────────────────────────────────────────────────

    def _record_clip(
        self,
        stream: RTSPReader,
        path: Path,
        duration_sec: float,
        first_frame: np.ndarray,
        stop: threading.Event,
    ) -> None:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        h, w = first_frame.shape[:2]
        writer = cv2.VideoWriter(str(path), fourcc, 20.0, (w, h))
        if not writer.isOpened():
            log.warning("VideoWriter 打开失败: %s", path)
            return
        try:
            writer.write(first_frame)
            deadline = time.monotonic() + duration_sec
            while time.monotonic() < deadline and not stop.is_set():
                frame = stream.read_frame()
                if frame is not None:
                    writer.write(frame)
        except Exception:
            log.exception("[%s] 视频录制异常", self._camera_id)
        finally:
            writer.release()

    def _append_timeline(
        self,
        date_dir: Path,
        start_iso: str,
        end_iso: str,
        event_type: str,
        snap_path: str | None,
        clip_path: str | None,
    ) -> None:
        csv_path = date_dir / "timeline.csv"
        exists = csv_path.exists()
        try:
            with open(csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not exists:
                    writer.writerow(_CSV_HEADER)
                writer.writerow([start_iso, end_iso, event_type, snap_path or "", clip_path or ""])
        except OSError:
            log.exception("[%s] 写入 timeline 失败: %s", self._camera_id, csv_path)
