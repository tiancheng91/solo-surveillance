# 配置最佳实践

## YOLO 模型选择

ultralytics 提供一系列 YOLOv8 模型，在大小与精度间有不同权衡。模型选择直接影响推理延迟——每次运动触发都会跑 YOLO。

| 模型 | 参数量 (M) | mAP@50-95 | 速度 | 推荐用途 |
|------|-----------|-----------|------|---------|
| `yolov8n.pt` | 3.2 | 37.3 | ★★★★★ | **默认**——对 CPU 友好，边缘设备可实时运行 |
| `yolov8s.pt` | 11.2 | 44.9 | ★★★★☆ | 均衡之选——精度更高，GPU 上依然快速 |
| `yolov8m.pt` | 25.9 | 50.2 | ★★★☆☆ | 较高精度——建议 GPU |
| `yolov8l.pt` | 43.7 | 52.9 | ★★☆☆☆ | 高精度——需要 GPU 实时 |
| `yolov8x.pt` | 68.2 | 53.9 | ★☆☆☆☆ | 极致精度——仅限 GPU |

> 在 Mac mini M4 上测试：`yolov8n` 约 15–25ms/帧，`yolov8s` 约 30–50ms/帧。CPU 设备建议用 n 或 s 系列。

配置方式：

```yaml
defaults:
  detectors:
    person:
      model: "yolov8s.pt"    # 换用更大的模型
      conf: 0.4               # 大模型可适当提高置信度阈值
```

## 运动检测调优

运动参数可针对不同场景调整，减少误触发或漏检。

| 场景 | diff_threshold | min_change_ratio | blur_ksize | 说明 |
|------|---------------|-----------------|-----------|------|
| 室内，受控照明 | 28（默认） | 0.012（默认） | 5（默认） | 通用敏感度 |
| 室外，有风/树 | 35–40 | 0.02–0.03 | 7 | 提高阈值抑制树叶晃动 |
| 低光 / 夜间 | 20–25 | 0.008–0.01 | 3 | 降低阈值补偿高噪声 |
| 高流量区域 | 28 | 0.03–0.05 | 7 | 更大变化量才触发，减少路过干扰 |
| 已裁剪区域 | 25 | 0.015–0.02 | 5 | 区域已过滤，适中即可 |

配置方式（全局）：

```yaml
defaults:
  motion:
    diff_threshold: 35        # 室外场景
    min_change_ratio: 0.02
    blur_ksize: 7
```

覆盖（单路相机）：

```yaml
cameras:
  - id: door
    motion:
      diff_threshold: 40      # 门口，减少路过触发
```

## AI 帧采集策略

```yaml
defaults:
  ai:
    frames: 3           # 运动触发后连续采集 3 帧
    interval_sec: 0.5   # 帧间隔 0.5 秒
    cooldown_sec: 10    # 检测冷却 10 秒
```

- **frames: 1** — 单帧模式，速度快但可能漏检快速动作
- **frames: 3** — 推荐值，YOLO 多帧取最高分，LLM 看多帧时序
- **frames: 5+** — 更长时间窗口，适合慢动作场景（如婴儿睡觉监控）
- **interval_sec** — 越小越密集，越大覆盖时间窗口越宽
- **cooldown_sec** — 防止频繁调用 LLM API，建议 10–60 秒

## 录制策略

```yaml
defaults:
  recordings:
    motion:             # 运动触发（无 AI 确认）
      snapshot: false
      clip: false
    person:             # YOLO 检测到人
      snapshot: true
      clip: true
      clip_seconds: 15
    llm_feeding:        # LLM 检测到喂奶
      snapshot: true
      clip: true
      clip_seconds: 30
```

- `motion` — 仅运动触发，建议 `snapshot: false`（太多无效触发）
- `person` — 有人时才录，建议开启 snapshot
- `llm_*` — LLM 确认的场景，建议保存较长的 clip（15–30 秒）

## LLM 场景配置

```yaml
llm:
  provider: "openai"
  model: "gpt-5-mini"
  api_key: "${LLM_API_KEY}"
  cooldown_sec: 60       # LLM 每分钟最多调用一次
  resize_width: 640      # 图片缩放到 640px 宽，节省 token

defaults:
  detectors:
    llm_vision:
      enabled: true
      conf: 0.6
      scenes:
        crying: "婴儿哭闹、表情痛苦"
        feeding: "婴儿正在吃奶"
```

场景描述的技巧：
- **描述场景状态**而非动作方向，如 `"婴儿在睡觉"` 优于 `"婴儿闭着眼睛"` 
- **每个场景一行**，避免过于具体的细节
- **首次配置时调低 `conf` 到 0.3**，用 `-v` 运行查看 LLM 实际返回的置信度
- 事件类型自动加 `llm_` 前缀，如 `crying` → `llm_crying`

## 常见场景组合

### 婴儿房监控

```yaml
llm:
  cooldown_sec: 30

defaults:
  motion:
    diff_threshold: 25
    min_change_ratio: 0.008

  ai:
    frames: 5
    interval_sec: 0.3

  detectors:
    llm_vision:
      enabled: true
      conf: 0.5
      scenes:
        crying: "婴儿哭闹、表情痛苦"
        feeding: "婴儿正在吃奶"
        changing: "正在换尿布"

  recordings:
    llm_crying:
      snapshot: true
      clip: true
      clip_seconds: 30
    llm_feeding:
      snapshot: true
      clip: true
      clip_seconds: 20
```

### 门口监控

```yaml
cameras:
  - id: door
    motion:
      diff_threshold: 40
      min_change_ratio: 0.03
    ai:
      frames: 3
    detectors:
      person:
        conf: 0.5
    recordings:
      person:
        snapshot: true
        clip: true
        clip_seconds: 15
```
