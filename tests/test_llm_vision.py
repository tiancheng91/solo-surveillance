"""Integration test for LLMVisionDetector using real API.

Usage:
    export LLM_API_BASE="https://your-api.example.com/v1"
    export LLM_API_KEY="your_token"
    export LLM_MODEL="gpt-5"
    uv run pytest tests/test_llm_vision.py -v -s
"""

import os
from pathlib import Path

import cv2
import pytest

_HERE = Path(__file__).parent.resolve()
_PROJECT_ROOT = _HERE.parent
_DEFAULT_IMAGE = _PROJECT_ROOT / "docs" / "test_person.jpg"

_API_BASE = os.environ.get("LLM_API_BASE", "")
_API_KEY = os.environ.get("LLM_API_KEY", "")
_MODEL = os.environ.get("LLM_MODEL", "gpt-5")


def _has_image() -> bool:
    return _DEFAULT_IMAGE.is_file()


def _load_frame(path: Path):
    frame = cv2.imread(str(path))
    if frame is None:
        pytest.skip(f"无法加载图片: {path}")
    return frame


@pytest.mark.skipif(not _has_image(), reason=f"测试图片不存在: {_DEFAULT_IMAGE}")
@pytest.mark.skipif(not _API_KEY, reason="LLM_API_KEY 未设置")
class TestLLMVisionDetector:
    """Real API integration tests for LLMVisionDetector."""

    @pytest.fixture
    def detector(self):
        from surveillance.detectors.llm_vision import LLMVisionDetector

        cfg = {
            "enabled": True,
            "provider": "openai",
            "model": _MODEL,
            "api_key": _API_KEY,
            "base_url": _API_BASE,
            "conf": 0.3,
            "cooldown_sec": 0,
            "frames": 1,
            "scenes": {
                "person": "画面中有人",
                "baby": "画面中有婴儿",
                "feeding": "婴儿正在吃奶",
            },
        }
        return LLMVisionDetector(cfg)

    def test_single_frame(self, detector):
        """Single frame scene detection."""
        frame = _load_frame(_DEFAULT_IMAGE)
        result = detector.analyze(frame)
        assert result is not None
        assert isinstance(result.labels, dict)
        print(f"\n单帧结果: {result.labels}")
        # Should detect at least "person" in the image
        assert "person" in result.labels

    def test_multi_frame(self, detector):
        """Multi-frame scene detection with 2 copies of the same image."""
        detector.frames = 2
        from surveillance.detectors.base import VisionContext

        frame = _load_frame(_DEFAULT_IMAGE)
        ctx = VisionContext(camera_id="test")
        ctx.extra["llm_extra_frames"] = [frame.copy()]
        result = detector.analyze(frame, ctx)
        assert result is not None
        assert isinstance(result.labels, dict)
        print(f"\n多帧结果: {result.labels}")

    def test_custom_prompt_and_scenes(self, detector):
        """Custom system prompt with different scene definitions."""
        detector.system_prompt = "你是一个庭院监控助手。请分析画面中的活动。"
        detector.scenes = {
            "person": "有人在走动",
            "package": "有包裹或快递",
            "vehicle": "有车辆",
        }
        frame = _load_frame(_DEFAULT_IMAGE)
        result = detector.analyze(frame)
        assert result is not None
        print(f"\n自定义场景结果: {result.labels}")

    def test_invalid_image_returns_empty(self, detector):
        """Passing an empty/invalid frame should not crash."""
        import numpy as np

        empty = np.zeros((10, 10, 3), dtype=np.uint8)
        result = detector.analyze(empty)
        assert result is not None
        # empty frame may or may not detect anything — should not crash
        print(f"\n空白帧结果: {result.labels}")

    def test_cooldown_skip(self, detector):
        """Second call within cooldown should return empty labels."""
        detector.cooldown_sec = 9999  # long cooldown
        frame = _load_frame(_DEFAULT_IMAGE)
        first = detector.analyze(frame)
        assert first is not None
        second = detector.analyze(frame)
        assert second is not None
        assert second.labels == {}, f"期望冷却跳过，但得到: {second.labels}"
        print("\n冷却跳过验证通过")

    def test_close_reopens_client(self, detector):
        """Closing the detector should reset the client."""
        frame = _load_frame(_DEFAULT_IMAGE)
        result_before = detector.analyze(frame)
        assert result_before is not None
        detector.close()
        assert detector._client is None
        result_after = detector.analyze(frame)
        assert result_after is not None
        print("\nclose 重置验证通过")
