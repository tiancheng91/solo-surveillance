# Changelog

## 0.1.1 (2026-05-12)

### Features

- Per-camera region-of-interest: crop frame to normalized `[x1,y1,x2,y2]` before motion and AI detection; snapshots and clips still save at full resolution (#region config field)

### Project

- README: GitHub badges, Web UI screenshot, PyPI-first install flow (`uvx` / `pip`)
- README: restructure with features-first layout

## 0.1.0 (2026-05-12)

### Features

- Initial solo-surveillance release
- RTSP stream support with auto-reconnect
- ONVIF device discovery and RTSP address resolution
- Motion gate: frame-diff detection with configurable sensitivity
- Person detection via YOLOv8 (ultralytics)
- Vision burst: multi-frame sampling within configurable window
- Configurable recordings: snapshots and video clips per event type
- Event-based recording with timeline.csv index
- Built-in Web UI: filter by camera, date, time range
- Web UI timeline: yellow density segments, hour labels, drag-to-navigate
- Web UI sort toggle: ascending/descending time order
- Home Assistant REST API event integration
- Hook scripts: external command execution on events
- Configurable AI cooldown and motion check interval
- `solo-surveillance` CLI entry point

### Fixes

- RTSP buffer drain after skip_frames sleep to avoid HEVC decoder warnings
- Replace grab loop with time.sleep in skip_frames for lower CPU usage

### Project

- GitHub Actions CI: build verification on push/PR
- GitHub Actions publish: auto-publish to PyPI on `v*` tags
