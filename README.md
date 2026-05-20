# solo-surveillance

<p>
  <img alt="License" src="https://img.shields.io/github/license/tiancheng91/solo-surveillance?style=flat-square">
  <img alt="Python" src="https://img.shields.io/badge/python-%3E%3D3.11-blue?style=flat-square">
  <img alt="Platform" src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey?style=flat-square">
  <img alt="Last Commit" src="https://img.shields.io/github/last-commit/tiancheng91/solo-surveillance?style=flat-square">
  <a href="https://zread.ai/tiancheng91/solo-surveillance"><img alt="zread" src="https://img.shields.io/badge/Ask_Zread-_.svg?style=flat&color=00b0aa&labelColor=000000&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQuOTYxNTYgMS42MDAxSDIuMjQxNTZDMS44ODgxIDEuNjAwMSAxLjYwMTU2IDEuODg2NjQgMS42MDE1NiAyLjI0MDFWNC45NjAxQzEuNjAxNTYgNS4zMTM1NiAxLjg4ODEgNS42MDAxIDIuMjQxNTYgNS42MDAxSDQuOTYxNTZDNS4zMTUwMiA1LjYwMDEgNS42MDE1NiA1LjMxMzU2IDUuNjAxNTYgNC45NjAxVjIuMjQwMUM1LjYwMTU2IDEuODg2NjQgNS4zMTUwMiAxLjYwMDEgNC45NjE1NiAxLjYwMDFaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00Ljk2MTU2IDEwLjM5OTlIMi4yNDE1NkMxLjg4ODEgMTAuMzk5OSAxLjYwMTU2IDEwLjY4NjQgMS42MDE1NiAxMS4wMzk5VjEzLjc1OTlDMS42MDE1NiAxNC4xMTM0IDEuODg4MSAxNC4zOTk5IDIuMjQxNTYgMTQuMzk5OUg0Ljk2MTU2QzUuMzE1MDIgMTQuMzk5OSA1LjYwMTU2IDE0LjExMzQgNS42MDE1NiAxMy43NTk5VjExLjAzOTlDNS42MDE1NiAxMC42ODY0IDUuMzE1MDIgMTAuMzk5OSA0Ljk2MTU2IDEwLjM5OTlaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik0xMy43NTg0IDEuNjAwMUgxMS4wMzg0QzEwLjY4NSAxLjYwMDEgMTAuMzk4NCAxLjg4NjY0IDEwLjM5ODQgMi4yNDAxVjQuOTYwMUMxMC4zOTg0IDUuMzEzNTYgMTAuNjg1IDUuNjAwMSAxMS4wMzg0IDUuNjAwMUgxMy43NTg0QzE0LjExMTkgNS42MDAxIDE0LjM5ODQgNS4zMTM1NiAxNC4zOTg0IDQuOTYwMVYyLjI0MDFDMTQuMzk4NCAxLjg4NjY0IDE0LjExMTkgMS42MDAxIDEzLjc1ODQgMS42MDAxWiIgZmlsbD0iI2ZmZiIvPgo8cGF0aCBkPSJNNCAxMkwxMiA0TDQgMTJaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00IDEyTDEyIDQiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K&logoColor=ffffff"></a>
</p>

自托管、轻量、纯本地运行的 AI 监控 NVR 系统。支持 RTSP 直连与 ONVIF 自动发现，YOLOv8 人体检测，内置 Web 回放界面与 Home Assistant 集成。

![Web UI 截图](docs/webui.png)

## 特性

- **多路相机** — 单进程多线程，每路独立配置，独立运行
- **双协议接入** — `rtsp://` 直连或 `onvif://` 自动发现 RTSP 地址
- **运动门控** — 帧差检测预过滤，无效帧不送 AI，大幅降低算力消耗
- **AI 检测** — 内置 YOLOv8 人体检测，支持自定义检测器扩展
- **场景化录制** — 按事件类型（motion / person）独立配置是否保存截图或视频片段
- **Web UI** — 内置 HTTP 服务器，按相机/日期/时间段检索事件回放，带时间轴导航
- **Home Assistant 集成** — 检测到事件时通过 REST API 推送通知
- **Hook 脚本** — 事件触发时调用外部脚本，灵活联动其他系统
- **自动重连** — RTSP 断流自动恢复，适合 7x24 运行
- **纯本地运行** — 所有视频流、录像、AI 推理均在本地完成，无云依赖

## 快速开始

### 1. 安装

```bash
# 方式 A（推荐）——自动隔离环境，无需手动安装
uvx solo-surveillance

# 方式 B——全局安装
pip install solo-surveillance
```

### 2. 配置相机

```bash
curl -O https://raw.githubusercontent.com/tiancheng91/solo-surveillance/main/config.example.yaml
mv config.example.yaml config.yaml
```

编辑 `config.yaml`，填入相机地址：

```yaml
cameras:
  - id: door
    enabled: true
    stream_url: "rtsp://user:password@192.168.1.100:554/stream1"
```

也支持 ONVIF 自动发现：

```yaml
  - id: front_door
    stream_url: "onvif://admin:password@192.168.1.100:80?profile=0"
```

> 添加多路相机只需在 `cameras` 下继续追加条目。全局默认值在 `defaults` 中，每路相机可选择性覆盖。

### 3. 启动

```bash
solo-surveillance
```

首次启动会自动下载 YOLOv8 模型。看到如下日志即正常运行：

```
INFO  [cam-door] 线程启动: door
INFO  [cam-door] 已连接 RTSP
```

### 4. 打开 Web UI（可选）

```bash
solo-surveillance --http 0.0.0.0:8080
```

浏览器访问 `http://<设备IP>:8080`：

- 按相机、日期、时间段筛选事件
- 缩略图懒加载，点击放大查看截图
- 支持播放 MP4 视频片段
- 右侧时间轴：黄色时段表示有事件，拖拽可快速导航
- 排序切换：默认倒序（最新在前），点击翻转

> Web UI 仅用于本地网络回放，不会将视频上传到云端。

## 命令行参考

```bash
solo-surveillance            # 启动（默认读取当前目录 config.yaml）
solo-surveillance -v         # 调试模式——查看 motion 触发、AI 冷却等详细日志
solo-surveillance -c /path/to/config.yaml  # 指定配置路径
solo-surveillance --http :8080     # 启动 Web UI（默认端口 8080）
solo-surveillance --http 0.0.0.0:9090  # 指定监听地址和端口
```

---

## Home Assistant 集成

支持将检测到的事件实时推送到 Home Assistant 事件总线，用于自动化联动（如灯光、报警、通知）。使用 Python 标准库实现，零额外依赖。

```yaml
hass:
  enabled: true
  url: "http://homeassistant:8123"
  token: "${HASS_TOKEN}"
```

配置后，每个事件（`camera.motion`、`camera.person`、`camera.feeding` 等）会自动 POST 到 HA 的 `/api/events/{event_type}`。

> 详细配置说明见 [docs/homeassistant.md](docs/homeassistant.md)。

---

*以下章节面向进阶用户，详细介绍配置选项与系统设计。*

---

## 配置详解

YAML 格式，`defaults` 块设置全局默认值，`cameras` 列表中每路相机可选择性覆盖。配置值支持 `${ENV_VAR}` 环境变量替换。

```yaml
# ───────── 全局默认值 ─────────
defaults:

  # ─── 运动检测 ───
  motion:
    resize_width: 320        # 帧缩放到此宽度再比对，值越小越快但越不精确
    blur_ksize: 7            # 高斯模糊核大小（奇数），越大对噪点越不敏感
    diff_threshold: 28       # 像素差值阈值（0-255），越大越不容易触发
    min_change_ratio: 0.012  # 变化像素占比阈值（1.2%），超过此值判定为运动
    ai_cooldown_sec: 10.0    # AI 检测冷却（秒），触发后在此时间内不再重复检测
    check_interval_sec: 0.2  # 运动检测采样间隔（秒）；0=每帧检测，>0 跳过中间帧降低 CPU

  # ─── 多帧爆发采样 ───
  # 开启后 motion 触发时短时间内连续采集多帧分别推理，结果合并取最高置信度
  vision_burst:
    enabled: false           # true=启用（提高检测准确率，增加算力消耗）
    window_sec: 1.2          # 采样窗口长度（秒）
    interval_sec: 0.3        # 相邻采样间隔（秒）
    min_interval_sec: 0.05   # 最小采样间隔下限，防止 CPU 满载

  # ─── 事件录制 ───
  recordiings:
    base_dir: "data"          # 录制文件根目录
    motion:                   # 运动触发（AI 检测前，记录所有画面变动）
      snapshot: false         # 是否保存截图
      clip: false             # 是否保存视频片段
      clip_seconds: 5         # 视频片段时长（秒）
    person:                   # AI 检测到人
      snapshot: true          # 建议开启
      clip: false
      clip_seconds: 10

  # ─── AI 检测器 ───
  detectors:
    person:                            # 人体检测器
      enabled: true
      model: "yolov8n.pt"             # YOLO 模型文件（首次自动下载，可选 yolov8s.pt 等）
      conf: 0.35                       # 检测置信度阈值（0-1）
      classes: [0]                     # COCO 类别 ID，[0] 代表人；空列表检测所有类别

  # ─── 外部 Hook 脚本（可选） ───
  hooks:
    person:
      - command: /path/to/notify.sh
    # motion:
    #   - command: /path/to/motion.sh


# ───────── 相机列表 ─────────
cameras:
  - id: xiaomi1               # 相机唯一标识
    enabled: true             # false=禁用此路
    stream_url: "rtsp://..."  # rtsp:// 直连或 onvif:// 自动发现

    # 以下字段可选，不写则回退到 defaults
    # motion:
    #   min_change_ratio: 0.02
    # detectors:
    #   person:
    #     conf: 0.4
```

> **ONVIF URL 格式**：`onvif://username:password@host:port?profile=N`  
> - `profile`：media profile 索引，默认 0  
> - 支持 `${ENV_VAR}` 避免明文密码：`onvif://admin:${CAM_PASSWORD}@192.168.1.100`

> **提示**：`config.yaml` 建议加入 `.gitignore`，避免泄露摄像头地址和凭据。

## 数据流

```
RTSP / ONVIF 流 ──> MotionGate (帧差门控)
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

```
data/
  {camera_id}/
    {date}/
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

事件触发时调用外部命令，用于发送通知、联动其他系统：

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
--snapshot-path snapshots/140530_person.jpg
--clip-path clips/140530_person.mp4
--labels '{"person": 0.85}'
```

## 检测器扩展

内置 `PersonYoloDetector`（YOLOv8 人体检测），可按以下步骤添加自定义检测器：

1. 继承 `VisionDetector` 或 `AudioDetector`（`surveillance/detectors/base.py`）
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
| `onvif.py` | ONVIF 设备连接、RTSP 地址发现 |
| `motion.py` | MotionGate — 帧差运动门控 |
| `detectors/base.py` | 检测器抽象基类与结果数据结构 |
| `detectors/person_yolo.py` | YOLOv8 人体检测 |
| `detectors/pipeline.py` | AIPipeline — 调度检测器，阈值门控 |
| `vision_burst.py` | 多帧爆发采样、合并与最佳帧选取 |
| `recordings.py` | 截图/视频录制 + timeline.csv 管理 |
| `hooks.py` | Hook 脚本管理器 |
| `hass.py` | Home Assistant REST API 事件推送 |
| `http_server.py` | 内置 HTTP 服务器 + Web UI |

### 线程模型

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
- onvif-zeep（>= 0.2.0，仅 ONVIF 需要；纯 RTSP 用户可忽略）

## License

MIT
