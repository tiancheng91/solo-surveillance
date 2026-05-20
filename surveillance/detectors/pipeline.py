from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from surveillance.detectors.person_yolo import PersonYoloDetector
from surveillance.detectors.base import (
    AudioContext,
    AudioDetector,
    AudioResult,
    VisionContext,
    VisionDetector,
    VisionResult,
)

log = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    vision: dict[str, VisionResult]
    audio: dict[str, AudioResult]

    def to_event_payload(self) -> dict:
        labels: dict[str, float] = {}
        raw: dict = {}
        for name, vr in self.vision.items():
            for k, v in vr.labels.items():
                key = f"{name}:{k}" if name else k
                labels[key] = v
            raw[name] = vr.raw
        for name, ar in self.audio.items():
            for k, v in ar.labels.items():
                key = f"{name}:{k}" if name else k
                labels[key] = v
            raw[name] = ar.raw
        return {"labels": labels, "detectors": raw}

    def significant(self, thresholds: dict[str, float]) -> dict[str, float]:
        out: dict[str, float] = {}
        flat: dict[str, float] = {}
        for vr in self.vision.values():
            flat.update(vr.labels)
        for ar in self.audio.values():
            flat.update(ar.labels)
        for k, v in flat.items():
            th = thresholds.get(k, 0.5)
            if v >= th:
                out[k] = v
        return out


class AIPipeline:
    """扩展：追加 VisionDetector / AudioDetector 实例即可。"""

    def __init__(
        self,
        vision_detectors: list[VisionDetector],
        audio_detectors: list[AudioDetector],
        label_thresholds: dict[str, float] | None = None,
    ) -> None:
        self._vision = vision_detectors
        self._audio = audio_detectors
        self.label_thresholds = dict(label_thresholds) if label_thresholds is not None else {}

    def has_vision_detectors(self) -> bool:
        return bool(self._vision)

    @staticmethod
    def from_camera_detectors(detectors_cfg: dict | None, llm_cfg: dict | None = None) -> AIPipeline:
        """仅根据合并后的 detectors 段构建（每路相机独立）。"""
        vision: list[VisionDetector] = []
        audio: list[AudioDetector] = []
        dc = detectors_cfg or {}
        thresholds: dict[str, float] = {}
        raw_person = dc.get("person")
        person_cfg: dict = raw_person if isinstance(raw_person, dict) else {}
        if person_cfg.get("enabled", True):
            p = person_cfg
            vision.append(
                PersonYoloDetector(
                    model=p.get("model", "yolov8n.pt"),
                    conf=float(p.get("conf", 0.35)),
                    classes=list(p.get("classes", [0])),
                )
            )
            thresholds["person"] = float(p.get("conf", 0.35))

        # LLM Vision detector
        raw_llm = dc.get("llm_vision")
        if isinstance(raw_llm, dict):
            from surveillance.detectors.llm_vision import LLMVisionDetector

            llm = LLMVisionDetector.from_config(llm_cfg, raw_llm)
            if llm:
                vision.append(llm)
                for scene in (raw_llm.get("scenes") or {}):
                    thresholds[f"llm_{scene}"] = float(raw_llm.get("conf", 0.6))

        return AIPipeline(vision, audio, label_thresholds=thresholds)

    def run(
        self,
        frame_bgr: np.ndarray,
        camera_id: str,
        rtsp_url: str | None = None,
        extra: dict | None = None,
        skip: set[str] | None = None,
    ) -> PipelineResult:
        vctx = VisionContext(camera_id=camera_id, extra=extra or {})
        vision_out: dict[str, VisionResult] = {}
        for d in self._vision:
            if skip and d.name in skip:
                continue
            try:
                vision_out[d.name] = d.analyze(frame_bgr, vctx)
            except Exception:
                log.exception("视觉检测器失败: %s", d.name)

        audio_out: dict[str, AudioResult] = {}
        if self._audio and rtsp_url:
            actx = AudioContext(rtsp_url=rtsp_url, camera_id=camera_id)
            for d in self._audio:
                try:
                    audio_out[d.name] = d.analyze(actx)
                except Exception:
                    log.exception("音频检测器失败: %s", d.name)

        return PipelineResult(vision=vision_out, audio=audio_out)

    def close(self) -> None:
        for d in self._vision + self._audio:
            try:
                d.close()
            except Exception:
                log.exception("关闭检测器: %s", getattr(d, "name", d))
