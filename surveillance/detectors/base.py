from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class VisionContext:
    """单次推理上下文，便于扩展（时间戳、相机 id 等）。"""

    camera_id: str = "default"
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class VisionResult:
    """视觉检测结果，统一结构便于 HA 与后续规则引擎使用。"""

    labels: dict[str, float]  # 事件名 -> 置信度 0~1
    raw: dict[str, Any] = field(default_factory=dict)


class VisionDetector(ABC):
    """画面变化后调用的视觉检测器，可并行注册多个。"""

    name: str = "vision"

    def analyze(self, frame_bgr, ctx: VisionContext | None = None) -> VisionResult:
        """单帧检测（默认走 batch）。"""
        return self.analyze_batch([frame_bgr], ctx)

    @abstractmethod
    def analyze_batch(
        self,
        frames: list[np.ndarray],
        ctx: VisionContext | None = None,
    ) -> VisionResult:
        """多帧检测，子类必须实现。鼓励支持批量推理。"""

    def close(self) -> None:
        pass


@dataclass
class AudioContext:
    rtsp_url: str
    camera_id: str = "default"
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class AudioResult:
    labels: dict[str, float]
    raw: dict[str, Any] = field(default_factory=dict)


class AudioDetector(ABC):
    """音频检测（如婴儿哭声），在运动触发后按需采样。"""

    name: str = "audio"

    @abstractmethod
    def analyze(self, ctx: AudioContext) -> AudioResult:
        """从 ctx.rtsp_url 拉音频或使用已缓存样本。"""

    def close(self) -> None:
        pass
