"""Tests for the YOLOv8 person detector."""

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


class TestPersonYoloDetector:
    """Tests for PersonYoloDetector using real YOLO model."""

    @pytest.fixture
    def detector(self):
        from surveillance.detectors.person_yolo import PersonYoloDetector

        return PersonYoloDetector(model="yolov8n.pt", conf=0.35)

    def test_detect_person(self, detector):
        """Should detect person in the test image with confidence > 0."""
        frame = _load_frame(_DEFAULT_IMAGE)
        result = detector.analyze(frame)
        assert result is not None
        assert "person" in result.labels
        assert result.labels["person"] >= 0.35
        print(f"\n检测结果: person={result.labels['person']:.4f}, raw={result.raw}")

    def test_empty_frame(self, detector):
        """Empty frame should return person=0.0."""
        empty = np.zeros((100, 100, 3), dtype=np.uint8)
        result = detector.analyze(empty)
        assert result is not None
        assert result.labels.get("person", 0) == 0.0
        print(f"\n空白帧结果: {result.labels}")

    def test_high_confidence_threshold(self):
        """Very high confidence threshold should still not crash."""
        from surveillance.detectors.person_yolo import PersonYoloDetector

        det = PersonYoloDetector(model="yolov8n.pt", conf=0.99)
        frame = _load_frame(_DEFAULT_IMAGE)
        result = det.analyze(frame)
        assert result is not None
        print(f"\n高阈值(0.99)结果: {result.labels}")

    def test_low_confidence_threshold(self):
        """Very low confidence threshold."""
        from surveillance.detectors.person_yolo import PersonYoloDetector

        det = PersonYoloDetector(model="yolov8n.pt", conf=0.01)
        frame = _load_frame(_DEFAULT_IMAGE)
        result = det.analyze(frame)
        assert result is not None
        assert "person" in result.labels
        print(f"\n低阈值(0.01)结果: person={result.labels['person']:.4f}")

    def test_different_resolution(self):
        """Should handle different resolution images."""
        from surveillance.detectors.person_yolo import PersonYoloDetector

        det = PersonYoloDetector(model="yolov8n.pt", conf=0.35)
        frame = _load_frame(_DEFAULT_IMAGE)
        small = cv2.resize(frame, (320, 240))
        result = det.analyze(small)
        assert result is not None
        print(f"\n低分辨率(320x240)结果: person={result.labels.get('person', 0):.4f}")
