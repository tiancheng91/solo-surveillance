"""Tests for AIPipeline — detector orchestration and result filtering."""

from pathlib import Path

import cv2
import numpy as np
import pytest

_HERE = Path(__file__).parent.resolve()
_PROJECT_ROOT = _HERE.parent
_DEFAULT_IMAGE = _PROJECT_ROOT / "docs" / "test_person.jpg"


def _load_frame(path: Path):
    frame = cv2.imread(str(path))
    if frame is None:
        pytest.skip(f"测试图片不存在: {path}")
    return frame


@pytest.fixture
def pipeline():
    from surveillance.detectors.pipeline import AIPipeline

    return AIPipeline.from_camera_detectors({
        "person": {"enabled": True, "model": "yolov8n.pt", "conf": 0.35},
    })


class TestAIPipeline:
    """Tests for AIPipeline orchestrator."""

    def test_run_returns_result(self, pipeline):
        """Pipeline.run() should return PipelineResult with vision results."""
        frame = _load_frame(_DEFAULT_IMAGE)
        result = pipeline.run(frame, camera_id="test_cam")
        assert result is not None
        assert "person_yolo" in result.vision
        vr = result.vision["person_yolo"]
        assert "person" in vr.labels
        print(f"\nPipeline 运行结果: person={vr.labels.get('person', 0):.4f}")

    def test_significant_filter(self, pipeline):
        """significant() should only return labels above threshold."""
        frame = _load_frame(_DEFAULT_IMAGE)
        result = pipeline.run(frame, camera_id="test_cam")
        sig = result.significant({"person": 0.0})
        assert "person" in sig
        sig_high = result.significant({"person": 0.99})
        assert "person" not in sig_high
        print(f"\n显著标签(threshold=0.0): {sig}")
        print(f"显著标签(threshold=0.99): {sig_high}")

    def test_to_event_payload(self, pipeline):
        """to_event_payload() should flatten labels with detector prefix."""
        frame = _load_frame(_DEFAULT_IMAGE)
        result = pipeline.run(frame, camera_id="test_cam")
        payload = result.to_event_payload()
        assert "labels" in payload
        assert "detectors" in payload
        print(f"\nEvent payload: {payload}")

    def test_no_detectors(self):
        """Pipeline with no vision/audio detectors should run without error."""
        from surveillance.detectors.pipeline import AIPipeline

        p = AIPipeline(vision_detectors=[], audio_detectors=[])
        assert not p.has_vision_detectors()
        frame = _load_frame(_DEFAULT_IMAGE)
        result = p.run(frame, camera_id="test_cam")
        assert result is not None
        assert result.vision == {}
        assert result.audio == {}

    def test_has_vision_detectors(self, pipeline):
        """has_vision_detectors() should return True when detectors are registered."""
        assert pipeline.has_vision_detectors()
