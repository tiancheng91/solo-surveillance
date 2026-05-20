# solo-surveillance

<p>
  <img alt="License" src="https://img.shields.io/github/license/tiancheng91/solo-surveillance?style=flat-square">
  <img alt="Python" src="https://img.shields.io/badge/python-%3E%3D3.11-blue?style=flat-square">
  <img alt="Platform" src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey?style=flat-square">
  <img alt="Last Commit" src="https://img.shields.io/github/last-commit/tiancheng91/solo-surveillance?style=flat-square">
  <a href="https://zread.ai/tiancheng91/solo-surveillance"><img alt="zread" src="https://img.shields.io/badge/Ask_Zread-_.svg?style=flat&color=00b0aa&labelColor=000000&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQuOTYxNTYgMS42MDAxSDIuMjQxNTZDMS44ODgxIDEuNjAwMSAxLjYwMTU2IDEuODg2NjQgMS42MDE1NiAyLjI0MDFWNC45NjAxQzEuNjAxNTYgNS4zMTM1NiAxLjg4ODEgNS42MDAxIDIuMjQxNTYgNS42MDAxSDQuOTYxNTZDNS4zMTUwMiA1LjYwMDEgNS42MDE1NiA1LjMxMzU2IDUuNjAxNTYgNC45NjAxVjIuMjQwMUM1LjYwMTU2IDEuODg2NjQgNS4zMTUwMiAxLjYwMDEgNC45NjE1NiAxLjYwMDFaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00Ljk2MTU2IDEwLjM5OTlIMi4yNDE1NkMxLjg4ODEgMTAuMzk5OSAxLjYwMTU2IDEwLjY4NjQgMS42MDE1NiAxMS4wMzk5VjEzLjc1OTlDMS42MDE1NiAxNC4xMTM0IDEuODg4MSAxNC4zOTk5IDIuMjQxNTYgMTQuMzk5OUg0Ljk2MTU2QzUuMzE1MDIgMTQuMzk5OSA1LjYwMTU2IDE0LjExMzQgNS42MDE1NiAxMy43NTk5VjExLjAzOTlDNS42MDE1NiAxMC42ODY0IDUuMzE1MDIgMTAuMzk5OSA0Ljk2MTU2IDEwLjM5OTlaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik0xMy43NTg0IDEuNjAwMUgxMS4wMzg0QzEwLjY4NSAxLjYwMDEgMTAuMzk4NCAxLjg4NjY0IDEwLjM5ODQgMi4yNDAxVjQuOTYwMUMxMC4zOTg0IDUuMzEzNTYgMTAuNjg1IDUuNjAwMSAxMS4wMzg0IDUuNjAwMUgxMy43NTg0QzE0LjExMTkgNS42MDAxIDE0LjM5ODQgNS4zMTM1NiAxNC4zOTg0IDQuOTYwMVYyLjI0MDFDMTQuMzk4NCAxLjg4NjY0IDE0LjExMTkgMS42MDAxIDEzLjc1ODQgMS42MDAxWiIgZmlsbD0iI2ZmZiIvPgo8cGF0aCBkPSJNNCAxMkwxMiA0TDQgMTJaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00IDEyTDEyIDQiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K&logoColor=ffffff"></a>
</p>

> [🇨🇳 中文](README.md) &nbsp; [🇯🇵 日本語](README.ja.md)

Self-hosted, lightweight, fully local AI surveillance NVR system. Supports RTSP direct connection and ONVIF auto-discovery, YOLOv8 person detection, built-in Web UI playback, and Home Assistant integration.

![Web UI Screenshot](docs/webui.png)

## Features

- **Multi-camera** — Single process, multi-threaded; each camera independently configured and running
- **Dual protocol** — `rtsp://` direct connection or `onvif://` auto-discover RTSP addresses
- **Motion gating** — Frame-diff pre-filtering skips non-event frames before AI, drastically reducing compute cost
- **AI detection** — Built-in YOLOv8 person detection, extensible with custom detectors
- **Scene-based recording** — Configure snapshot/video clip saving independently per event type (motion / person / llm_*)
- **Web UI** — Built-in HTTP server, filter events by camera/date/time range with timeline navigation
- **Home Assistant integration** — Push event notifications via REST API
- **Hook scripts** — Trigger external scripts on events for flexible integration
- **Auto-reconnect** — RTSP stream disconnection auto-recovery, suitable for 7x24 operation
- **Fully local** — All video streams, recordings, and AI inference run locally, no cloud dependency

## Quick Start

### 1. Install

```bash
# Option A (recommended) — auto-isolated environment, no manual setup
uvx solo-surveillance

# Option B — global install
pip install solo-surveillance
```

### 2. Configure cameras

```bash
curl -O https://raw.githubusercontent.com/tiancheng91/solo-surveillance/main/config.example.yaml
mv config.example.yaml config.yaml
```

Edit `config.yaml` with your camera details:

```yaml
cameras:
  - id: door
    enabled: true
    stream_url: "rtsp://user:password@192.168.1.100:554/stream1"
```

ONVIF auto-discovery is also supported:

```yaml
  - id: front_door
    stream_url: "onvif://admin:password@192.168.1.100:80?profile=0"
```

> See `config.example.yaml` for the complete configuration (LLM vision, HA integration, Hook scripts, etc.).

### 3. Launch

```bash
solo-surveillance
```

The YOLOv8 model downloads automatically on first run. You should see:

```
INFO  [cam-door] Thread started: door
INFO  [cam-door] Connected to RTSP
```

### 4. Open Web UI (optional)

```bash
solo-surveillance --http 0.0.0.0:8080
```

Open `http://<device-ip>:8080` in your browser:

- Filter events by camera, date, and time range
- Lazy-loaded thumbnails, click to enlarge
- MP4 clip playback support
- Right-side timeline: yellow segments indicate events, drag to navigate
- Sort toggle: newest-first by default, click to reverse

> Web UI is for local network playback only — no video is uploaded to the cloud.

## Command Line Reference

```bash
solo-surveillance            # Start (reads config.yaml from current directory)
solo-surveillance -v         # Debug mode — motion triggers, AI cooldown, etc.
solo-surveillance -c /path/to/config.yaml  # Custom config path
solo-surveillance --http :8080     # Start Web UI (default port 8080)
solo-surveillance --http 0.0.0.0:9090  # Custom listen address and port
```

---

## Home Assistant Integration

Push detected events to the Home Assistant event bus in real-time for automations (lights, alarms, notifications). Uses Python stdlib only, zero extra dependencies.

```yaml
hass:
  enabled: true
  url: "http://homeassistant:8123"
  token: "${HASS_TOKEN}"
```

Once configured, each event (`camera.motion`, `camera.person`, `camera.feeding`, etc.) is automatically POSTed to HA's `/api/events/{event_type}`.

> See [docs/homeassistant.md](docs/homeassistant.md) for detailed configuration.

---

*The following sections cover advanced configuration and system design.*

---

## Configuration

YAML format. The `defaults` block sets global defaults; each camera in the `cameras` list can selectively override them. Config values support `${ENV_VAR}` substitution.

Core structure:

```yaml
defaults:
  motion:         # Motion detection parameters
  ai:             # AI inference params (frame count, cooldown)
  recordings:     # Snapshots / video clips
  detectors:      # YOLO / LLM detectors
  region:         # Optional detection region

cameras:          # Camera list, each can override defaults

hass:             # Optional: Home Assistant integration
hooks:            # Optional: external scripts
llm:              # Optional: LLM API connection config
```

> See `config.example.yaml` for the full config with all options and detailed comments.
> See [docs/configuration.md](docs/configuration.md) for detailed configuration guide and best practices.
> See [docs/scenarios.md](docs/scenarios.md) for ready-to-use scenario presets.

> **ONVIF URL format**: `onvif://username:password@host:port?profile=N`
> - `profile`: media profile index, defaults to 0
> - Supports `${ENV_VAR}` to avoid plain-text passwords: `onvif://admin:${CAM_PASSWORD}@192.168.1.100`

> **Tip**: Add `config.yaml` to `.gitignore` to avoid leaking camera addresses and credentials.

## Data Flow

```
RTSP / ONVIF stream ──> MotionGate (frame-diff gating)
                          │
                   min_change_ratio ≥ threshold?
                          │no └─ skip
                          │yes
                   [AI cooldown check]
                          │
                   collect_frames() multi-frame capture
                          │
                   AIPipeline.run_batch() batch inference
                          │
                   significant label ≥ threshold?
                          │no └─ skip
                          │yes
                   Save snapshot/clip → append to timeline.csv
                          │
                   Notifier push (HA / Hook scripts)
```

## Recordings & Timeline

```
data/
  {camera_id}/
    {date}/
      snapshots/
        140530_person.jpg      # Event snapshot
      clips/
        140530_person.mp4      # Event video clip
      timeline.csv             # Daily event index
```

`timeline.csv` format:

```
start_time,end_time,event_type,snapshot_path,clip_path
2026-05-07T14:05:30,2026-05-07T14:05:35,person,snapshots/140530_person.jpg,clips/140530_person.mp4
```

Duplicate events of the same type are suppressed within 3 seconds to avoid consecutive repeated recordings.

## Hook Scripts

Hook scripts are configured at the root level of `config.yaml` (global — all scripts fire for every event type):

```yaml
# Optional: external scripts executed on events
hooks:
  - command: scripts/event_logger.sh
```

Each script receives CLI arguments:

```
--camera-id xiaomi1
--event-type person
--start-time 2026-05-07T14:05:30
--end-time 2026-05-07T14:05:35
--snapshot-path snapshots/140530_person.jpg
--clip-path clips/140530_person.mp4
--labels '{"person": 0.85}'
```

## Detector Extension

Built-in `PersonYoloDetector` (YOLOv8 person detection). Add custom detectors:

1. Subclass `VisionDetector` or `AudioDetector` from `surveillance/detectors/base.py`
2. Set a unique `name` class variable
3. Implement `analyze_batch()` returning `VisionResult` / `AudioResult` (receives multiple frames, decides how to use them)
4. Register in `AIPipeline.from_camera_detectors()`

```python
from surveillance.detectors.base import VisionDetector, VisionResult, VisionContext

class FireDetector(VisionDetector):
    name = "fire_detector"

    def analyze_batch(self, frames, ctx: VisionContext | None = None):
        # Fire detection logic...
        return VisionResult(labels={"fire": 0.92})
```

## Architecture

| Module | Responsibility |
|---|---|
| `main.py` | Entry point: argparse, thread management, signal handling |
| `config_loader.py` | YAML loading, deep_merge, env var substitution |
| `stream.py` | RTSPReader — cv2.VideoCapture wrapper, auto-reconnect |
| `onvif.py` | ONVIF device connection, RTSP address discovery |
| `motion.py` | MotionGate — frame-diff motion gating |
| `region.py` | Detection region cropping (normalized coordinates) |
| `detectors/base.py` | Detector abstract base classes and result data types |
| `detectors/person_yolo.py` | YOLOv8 person detection |
| `detectors/llm_vision.py` | LLM vision scene recognition |
| `detectors/pipeline.py` | AIPipeline — orchestrates detectors, threshold gating |
| `vision_burst.py` | Multi-frame collection helper (collect_frames) |
| `recordings.py` | Snapshot/clip recording + timeline.csv management |
| `notifiers/` | Notifier unified interface (HA + Hook scripts) |
| `http_server.py` | Built-in HTTP server + Web UI |

### Threading Model

- Each enabled camera gets its own `threading.Thread`
- `threading.Event` coordinates shutdown (SIGINT / SIGTERM)
- Each thread owns independent `RTSPReader`, `MotionGate`, `AIPipeline` (no shared state)
- HTTP server runs in a daemon thread, non-blocking
- Hook scripts execute in daemon threads (30s timeout)

## Dependencies

- Python >= 3.11
- opencv-python-headless (>= 4.8.0)
- numpy (>= 1.24.0)
- PyYAML (>= 6.0)
- ultralytics (>= 8.0.0)
- onvif-zeep (>= 0.2.0, ONVIF only; RTSP-only users can ignore)
- anthropic / openai (optional, required for LLM vision scene recognition)

## License

MIT
