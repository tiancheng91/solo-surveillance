# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run surveillance (prod mode, reads ./config.yaml)
uv run cam-surveillance

# Run with debug logging
uv run cam-surveillance -v

# Run with custom config path
uv run cam-surveillance -c /path/to/config.yaml

# Run directly via module
uv run python -m surveillance

# Install dependencies (after cloning)
uv sync

# Add a new dependency
uv add <package>
```

No test framework is currently set up (no tests exist in the repo).

## Architecture

**cam-surveillance** — multi-RTSP motion-triggered AI surveillance with Home Assistant integration.

### Data flow

```
RTSP stream ──> MotionGate (frame diff gating)
                     │
              trigger ratio ≥ threshold?
                     │
              [AI cooldown check]
                     │
              AIPipeline runs (single-frame or vision_burst)
                     │
              significant labels ≥ threshold?
                     │
              [HA notify cooldown check]
                     │
              Fire HA event + optional JPEG snapshot
```

### Package layout (`surveillance/`)

| Module | Responsibility |
|---|---|
| `main.py` | Entry point: argparse, thread-per-camera workers, signal handling |
| `config_loader.py` | YAML load with `deep_merge(defaults, camera)` and `${ENV_VAR}` expansion |
| `stream.py` | `RTSPReader` — cv2.VideoCapture with auto-reconnect and TCP transport |
| `motion.py` | `MotionGate` — resized → grayscale → gaussian blur → absdiff → threshold ratio |
| `detectors/base.py` | Abstract `VisionDetector` / `AudioDetector` + `VisionResult` / `AudioResult` dataclasses |
| `detectors/person_yolo.py` | `PersonYoloDetector` — YOLOv8 via ultralytics, outputs `person` label with confidence |
| `detectors/pipeline.py` | `AIPipeline` — runs all registered detectors, manages `thresholds` for significance gating |
| `hass.py` | `HassClient` — POSTs to Home Assistant REST API `/api/events/{event_type}` |
| `snapshots.py` | `save_trigger_snapshot` — writes JPEG to `data/{camera_id}/{timestamp}.jpg` |
| `vision_burst.py` | Multi-frame burst within `window_sec`, merges labels by max confidence, picks best frame for snapshot |

### Configuration

YAML with a `defaults` block + per-camera overrides merged via `deep_merge`. Config values support `${ENV_VAR}` substitution. See `config.example.yaml`.

### Detector extension pattern

1. Subclass `VisionDetector` or `AudioDetector` from `detectors/base.py`
2. Set a unique `name` class variable
3. Implement `analyze()` returning `VisionResult` / `AudioResult`
4. Register in `AIPipeline.from_camera_detectors()` or add config-driven instantiation

### Threading model

- One `threading.Thread` per enabled camera, all sharing one `HassClient`
- `threading.Event` for coordinated shutdown (SIGINT/SIGTERM)
- Each thread owns its own `RTSPReader`, `MotionGate`, `AIPipeline` instances (no shared state)
