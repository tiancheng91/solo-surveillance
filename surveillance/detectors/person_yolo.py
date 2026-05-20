from __future__ import annotations

import logging
from typing import Any

import numpy as np

from surveillance.detectors.base import VisionContext, VisionDetector, VisionResult

log = logging.getLogger(__name__)


class PersonYoloDetector(VisionDetector):
    """YOLOv8 人体检测；后续可换为自训练权重或 ONNX 推理类。"""

    name = "person_yolo"

    def __init__(
        self,
        model: str = "yolov8n.pt",
        conf: float = 0.35,
        classes: list[int] | None = None,
        device: str | None = None,
    ) -> None:
        from ultralytics import YOLO

        self._model = YOLO(model)
        self._conf = conf
        self._classes = classes if classes is not None else [0]
        self._device = device

    def analyze(self, frame_bgr: np.ndarray, ctx: VisionContext | None = None) -> VisionResult:
        return self.analyze_batch([frame_bgr], ctx)

    def analyze_batch(
        self,
        frames: list[np.ndarray],
        ctx: VisionContext | None = None,
    ) -> VisionResult:
        ctx = ctx or VisionContext()
        kwargs: dict[str, Any] = {
            "conf": self._conf,
            "classes": self._classes,
            "verbose": False,
        }
        if self._device:
            kwargs["device"] = self._device

        best_person = 0.0
        total_boxes = 0
        for frame_bgr in frames:
            results = self._model.predict(frame_bgr, **kwargs)
            if results and results[0].boxes is not None and len(results[0].boxes):
                total_boxes = max(total_boxes, len(results[0].boxes))
                conf = float(results[0].boxes.conf.max().item())
                if conf > best_person:
                    best_person = conf

        labels = {"person": min(1.0, best_person) if total_boxes else 0.0}
        log.debug(
            "person_yolo: camera_id=%s frames=%d boxes=%s person_conf=%.4f",
            ctx.camera_id,
            len(frames),
            total_boxes,
            labels["person"],
        )
        return VisionResult(
            labels=labels,
            raw={"boxes": total_boxes, "frames": len(frames), "camera_id": ctx.camera_id},
        )

    def close(self) -> None:
        # ultralytics 无统一 close，依赖进程退出
        pass
