# solo-surveillance

自托管、轻量、纯本地运行的 AI 监控 NVR 系统，支持 Web UI 回放与 Home Assistant 集成。

### 设计理念

**Solo** 代表这套系统的三个核心追求：

- **独立自主（Independence）** — 不依赖任何第三方云服务，所有视频流、录像和分析均在本地完成。A self-hosted, cloud-independent NVR solution.
- **单机高效（Single-node）** — 专为单机部署优化（Mac mini M4、NAS、Docker 容器），无需复杂集群即可稳定运行。Designed for single-node efficiency.
- **专注纯粹（Focus）** — 只做好"监控与录制"这一件事，拒绝功能臃肿。A focused approach to home security.

## 快速开始

### 前置要求

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/)（推荐）或 pip
- 一个或多个 RTSP 摄像头

> **没有 RTSP 摄像头？** 推荐搭配 [go2rtc](https://github.com/AlexxIT/go2rtc) 使用——它可以将市面上绝大多数摄像头协议（ONVIF、RTMP、HTTP-FLV、海康/大华私有协议等）统一转换为 RTSP 流，甚至支持 USB 摄像头和手机摄像头接入。配合本项目的 `config.example.yaml` 中的示例地址即可开箱即用。

### 1. 克隆 & 安装

```bash
git clone https://github.com/tiancheng91/solo-surveillance.git && cd solo-surveillance
uv sync
```

### 2. 配置相机

```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml`，填入你的 RTSP 相机地址：

```yaml
cameras:
  - id: door           # 相机名称，自定义
    enabled: true
    rtsp_url: "rtsp://user:password@192.168.1.100:554/stream1"
```

> 添加多路相机只需在 `cameras` 列表下继续追加条目。全局默认值在 `defaults` 中，单路可选择性覆盖。

### 3. 启动

```bash
uv run solo-surveillance
```

首次启动会自动下载 YOLOv8 模型。看到如下日志即正常运行：

```
INFO  [cam-door] 线程启动: door
INFO  [cam-door] 已连接 RTSP
```

### 4. （可选）打开 Web UI

```bash
uv run solo-surveillance --http :8080
```

浏览器访问 `http://<设备IP>:8080`，按相机/日期查看截图与录像回放。

> Web UI 仅用于本地网络回放，不会将视频上传到云端。

### 效果预览

```
默认配置下：
  画面变化 → 运动触发（MotionGate 过滤无效帧）
  → AI 检测 → 检测到人 → 保存截图 + 通知
  检测不到人 → 跳过，不浪费算力
```

## 特性

- **多路相机** — 单进程多线程，每路独立配置
- **运动门控** — 帧差检测（resize → 灰度 → 高斯模糊 → absdiff），AI 前过滤无效帧
- **AI 检测** — YOLOv8 人体检测（可扩展更多检测器）
- **Vision Burst** — 短窗口多帧采样，置信度合并，截图选最佳帧
- **场景化录制** — 按事件类型（motion / person）独立配置截图与视频片段
- **Web UI** — 内置 HTTP 服务器，按相机/日期/时间段查询回放
- **Home Assistant** — REST API 事件推送（可选，需在配置中设置）
- **Hook 脚本** — 事件触发时调用外部脚本，灵活扩展
- **自动重连** — RTSP 断流自动重连，守护运行

## 命令行

```bash
# 启动（默认读取当前目录 config.yaml）
uv run solo-surveillance

# 调试模式（查看 motion 触发、AI 冷却、检测结果等详细日志）
uv run solo-surveillance -v

# 自定义配置路径
uv run solo-surveillance -c /path/to/config.yaml

# 启动内置 Web UI（监听所有网卡，端口 8080）
uv run solo-surveillance --http :8080

# 指定地址和端口
uv run solo-surveillance --http 0.0.0.0:9090
```

## Web UI

启动时加 `--http :8080`，浏览器打开 `http://<设备IP>:8080`：

- 按相机、日期、时间段筛选事件
- 查看截图缩略图（懒加载，滚动到可视区域自动加载）
- 点击缩略图放大查看，支持播放视频片段（MP4）
- 事件类型按颜色区分：`person` 粉色 / `motion` 琥珀色

---

以下章节面向进阶用户，详细介绍配置选项与系统设计。

---

## 配置

YAML 格式，`defaults` 块设置全局默认值，`cameras` 列表中每路相机可选择性覆盖。配置值支持 `${ENV_VAR}` 环境变量替换。

### 配置详解

```yaml
# ───────── 全局默认值 ─────────
# 所有 cameras 中未显式配置的字段都会回退到这里
defaults:

  # ─── 运动检测 ───
  motion:
    resize_width: 320        # 帧缩放到此宽度再比对，值越小越快但越不精确
    blur_ksize: 7            # 高斯模糊核大小（奇数），越大对噪点越不敏感
    diff_threshold: 28       # 像素差值阈值（0-255），越大越不容易触发
    min_change_ratio: 0.012  # 变化像素占比阈值，超过此值判定为运动（1.2%）
    ai_cooldown_sec: 10.0    # AI 检测冷却时间（秒），运动触发后在此时间内不再重复检测

  # ─── 多帧爆发采样 ───
  # 开启后 motion 触发时在短时间内连续采集多帧分别推理，结果合并取最高置信度
  vision_burst:
    enabled: false           # true=启用（提高检测准确率，增加算力消耗）
    window_sec: 1.2          # 采样窗口长度（秒）
    interval_sec: 0.3        # 相邻采样间隔（秒）
    min_interval_sec: 0.05   # 最小采样间隔下限，防止配置过小导致 CPU 满载

  # ─── 事件录制 ───
  recordiings:
    base_dir: "data"          # 录制文件根目录
    motion:                   # 运动触发（AI 检测前，记录所有画面变动）
      snapshot: false         # 是否保存截图
      clip: false             # 是否保存视频片段
      clip_seconds: 5         # 视频片段时长（秒）
    person:                   # AI 检测到人
      snapshot: true          # 建议开启，保存检测到人时的截图
      clip: false             # 视频片段
      clip_seconds: 10

  # ─── AI 检测器 ───
  detectors:
    person:                            # 人体检测器
      enabled: true                    # 是否启用
      model: "yolov8n.pt"             # YOLO 模型文件（首次自动下载，可选 yolov8s.pt 等）
      conf: 0.35                       # 检测置信度阈值（0-1），越高误报越少但可能漏检
      classes: [0]                     # COCO 类别 ID，[0] 代表人；空列表检测所有类别

  # ─── 外部 Hook 脚本（可选） ───
  hooks:
    person:                            # 检测到人时触发
      - command: /path/to/notify.sh    # 可执行脚本路径
    # motion:                          # 运动触发时（AI 检测前）
    #   - command: /path/to/motion.sh


# ───────── 相机列表 ─────────
cameras:
  - id: xiaomi1               # 相机唯一标识，用于日志、目录命名
    enabled: true             # false=禁用此路，不会创建线程
    rtsp_url: "rtsp://..."    # RTSP 流地址

    # 以下字段可选，不写则回退到 defaults 中的对应值：
    # motion:
    #   min_change_ratio: 0.02
    # detectors:
    #   person:
    #     enabled: true
    #     conf: 0.4
    # recordings:
    #   person:
    #     clip_seconds: 15

  # - id: cam2               # 多路示例（取消注释启用）
  #   enabled: false
  #   rtsp_url: "rtsp://..."
  #   detectors:
  #     person:
  #       enabled: false
```

> **提示**：`config.yaml` 建议加入 `.gitignore`，避免泄露摄像头地址和凭据。

## 数据流

```
RTSP stream ──> MotionGate (帧差门控)
                     │
              min_change_ratio ≥ threshold?
                     │否└─ 跳过
                     │是
              [AI cooldown 冷却检查]
                     │
              AIPipeline 运行（单帧 / vision_burst）
                     │
              显著标签 ≥ threshold?
                     │否└─ 跳过
                     │是
              录制截图/视频 → 追加 timeline.csv
                     │
              Hook 脚本触发 / HA 事件推送
```

## 录制与 Timeline

数据存储在 `data/{camera_id}/{date}/` 目录：

```
data/
  xiaomi1/
    2026-05-07/
      snapshots/
        140530_person.jpg      # 事件截图
      clips/
        140530_person.mp4      # 事件视频片段
      timeline.csv             # 本日事件索引
```

`timeline.csv` 格式：

```
start_time,end_time,event_type,snapshot_path,clip_path
2026-05-07T14:05:30,2026-05-07T14:05:35,person,snapshots/140530_person.jpg,clips/140530_person.mp4
```

同类型事件 3 秒内防重，避免连续重复录制。

## Hook 脚本

配置中定义事件触发时调用的外部命令，用于发送通知、联动其他系统等：

```yaml
defaults:
  hooks:
    person:
      - command: /path/to/notify.sh
```

Hook 接收命令行参数：

```
--camera-id xiaomi1
--event-type person
--start-time 2026-05-07T14:05:30
--end-time 2026-05-07T14:05:35
--snapshot-path snapshots/140530_person.jpg   # 截图相对路径（如有）
--clip-path clips/140530_person.mp4           # 视频相对路径（如有）
--labels '{"person": 0.85}'                   # JSON 格式标签与置信度
```

## 检测器扩展

内置 `PersonYoloDetector`（YOLOv8 人体检测），可按以下步骤添加自定义检测器：

1. 继承 `VisionDetector` 或 `AudioDetector`（`detectors/base.py`）
2. 设置唯一 `name` 类变量
3. 实现 `analyze()` 返回 `VisionResult` / `AudioResult`
4. 在 `AIPipeline.from_camera_detectors()` 中注册

```python
from surveillance.detectors.base import VisionDetector, VisionResult, VisionContext

class FireDetector(VisionDetector):
    name = "fire_detector"

    def analyze(self, frame_bgr, ctx: VisionContext | None = None):
        # 火焰检测逻辑...
        return VisionResult(labels={"fire": 0.92})
```

## 架构

| 模块 | 职责 |
|---|---|
| `main.py` | 入口：argparse、线程管理、信号处理 |
| `config_loader.py` | YAML 加载、deep_merge、环境变量展开 |
| `stream.py` | RTSPReader — cv2.VideoCapture 封装，自动重连 |
| `motion.py` | MotionGate — 帧差运动门控 |
| `detectors/base.py` | VisionDetector / AudioDetector 抽象基类与结果数据结构 |
| `detectors/person_yolo.py` | YOLOv8 人体检测 |
| `detectors/pipeline.py` | AIPipeline — 调度所有检测器，阈值门控 |
| `vision_burst.py` | 多帧爆发采样、合并与最佳帧选取 |
| `recordings.py` | 截图/视频录制 + timeline.csv 管理 |
| `hooks.py` | Hook 脚本管理器 |
| `hass.py` | Home Assistant REST API 事件推送 |
| `http_server.py` | 内置 HTTP 服务器 + Web UI |

## 线程模型

- 每路已启用相机创建独立 `threading.Thread`
- `threading.Event` 协调关闭（SIGINT / SIGTERM）
- 每线程持有独立 `RTSPReader`、`MotionGate`、`AIPipeline`（无共享状态）
- HTTP 服务器在守护线程中运行，不阻塞主流程
- Hook 脚本在独立守护线程中执行（30s 超时自动终止）

## 依赖

- Python >= 3.11
- opencv-python-headless（>= 4.8.0）
- numpy（>= 1.24.0）
- PyYAML（>= 6.0）
- ultralytics（>= 8.0.0）

## License

MIT
