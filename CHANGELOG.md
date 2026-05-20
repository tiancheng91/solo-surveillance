# Changelog

## 0.3.1 (2026-05-20)

### Fixes

- Ctrl+C 无法退出程序：`read_frame()`/`skip_frames()` 新增 `stop` 事件参数，阻塞操作分段轮询退出信号（#stream, #recordings）
- 清理死代码：移除已无调用方的 `_vision_burst_cfg` 和 `rtsp_url` 备选 key
- `motion.blur_ksize` 默认值改为 7，与 `config.example.yaml` 一致

### Project

- 补充 MIT LICENSE 文件
- 新增英文/日文 README 翻译
- README 结构重构：新增"工作原理"、功能表格、项目结构树
- 新增 CI 测试步骤、PyPI/CI 状态徽章
- 新增 CONTRIBUTING.md 和 Issue/PR 模板
- 创建 GitHub Releases（v0.1.0 ~ v0.3.0）

## 0.3.0 (2026-05-13)

### Features

- Batch inference interface: `VisionDetector.analyze_batch(frames)` replaces single-frame API; YOLO multi-frame merge, LLM multi-image API call unified
- Unified AI frame collection: `ai.frames` / `ai.interval_sec` replaces `vision_burst` + `llm_vision.frames`
- LLM config split: global `llm` section (connection) + `detectors.llm_vision` (scenes), per-camera scene override
- `llm_` prefix on LLM scene event types to avoid collision with YOLO labels
- Image resize before LLM API call (`resize_width`, default 640) for cost efficiency
- Dynamic event type colors in Web UI (hash-based HSL)
- Config docs: YOLO model selection guide, motion tuning table, 3 preset scenarios

### Refactor

- Notifier interface: `HassNotifier` + `HooksNotifier` under `surveillance/notifiers/` with common `Notifier` base
- `vision_burst.py` simplified to `collect_frames()` utility

### Project

- CI workflow targets `main` branch
- `docs/configuration.md`: best practices for YOLO models, motion tuning, LLM scenes
- `docs/scenarios.md`: ready-to-use configs for motion-only, person detection, LLM baby room

## 0.2.0 (2026-05-12)

### Features

- LLM vision scene detection: analyze motion-triggered frames via Anthropic/OpenAI API to detect complex scenes (feeding, crying, diaper change, etc.)
- Custom scene definitions: user-defined scene keys and descriptions in config, LLM returns confidence scores for each
- Independent LLM cooldown: configurable API call interval (default 60s), separate from YOLO cooldown
- Provider support: Anthropic Claude (`claude-sonnet-4-20250514`) and OpenAI GPT-4o
- Custom API endpoint: `base_url` config for API proxy/gateway
- Multi-frame support: `frames` config (>1 sends multiple keyframes spaced >0.5s for better temporal context)
- Scene labels flow through existing recording/hook/HA pipeline automatically

### Project

- New optional dependency: `uv sync --group llm` or `uv add anthropic` for LLM support

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
