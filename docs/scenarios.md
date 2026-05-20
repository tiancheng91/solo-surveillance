# 场景配置示例

以下配置可直接复制对应段落到 `config.yaml` 中使用。

## 场景 1：画面变动检测

**适用场景**：门口、庭院等只需知道"画面有变化"的简单场景。不启用 AI，只做运动检测。

```yaml
defaults:
  motion:
    resize_width: 320
    blur_ksize: 7
    diff_threshold: 28
    min_change_ratio: 0.012
    check_interval_sec: 0.2

  recordings:
    motion:
      snapshot: true          # 运动时截图，方便查看
      clip: false

  detectors:
    person:
      enabled: false          # 不启用 YOLO，只做运动检测

cameras:
  - id: door
    enabled: true
    stream_url: "rtsp://..."
```

效果：画面变化时保存一张快照，不调用 AI，功耗最低。

---

## 场景 2：人在检测

**适用场景**：需要准确知道"是否有人"的场景（如办公室、仓库）。启用 YOLO 人体检测，运动触发后确认是否是人，减少误报。

```yaml
defaults:
  motion:
    resize_width: 320
    blur_ksize: 7
    diff_threshold: 28
    min_change_ratio: 0.012
    check_interval_sec: 0.2

  ai:
    frames: 3                 # 多帧采样，YOLO 取最高置信度
    interval_sec: 0.5
    cooldown_sec: 10.0

  detectors:
    person:
      enabled: true
      model: "yolov8n.pt"
      conf: 0.35

  recordings:
    motion:
      snapshot: false
      clip: false
    person:
      snapshot: true          # 检测到人时截图
      clip: false

cameras:
  - id: office
    enabled: true
    stream_url: "rtsp://..."
```

效果：仅当 YOLO 确认有人时才保存截图，忽略空场景的晃动。

---

## 场景 3：带 LLM 的婴儿房监控

**适用场景**：需要理解"正在发生什么"的复杂场景（婴儿房、老人看护）。运动触发 → YOLO 确认 → LLM 理解场景（喂奶、哭闹、换尿布）。

```yaml
llm:
  provider: "openai"                  # 或 "anthropic"
  model: "gpt-5-mini"
  api_key: "${LLM_API_KEY}"           # 建议用环境变量
  cooldown_sec: 30
  resize_width: 640                   # 缩小图片节省 token 费用

defaults:
  motion:
    resize_width: 320
    blur_ksize: 5
    diff_threshold: 25                # 略低，对婴儿微小动作更敏感
    min_change_ratio: 0.008
    check_interval_sec: 0.2

  ai:
    frames: 5                         # 更多帧让 LLM 看到时序变化
    interval_sec: 0.3
    cooldown_sec: 10.0

  detectors:
    person:
      enabled: true
      model: "yolov8n.pt"
      conf: 0.3                       # 低阈值，确保不遗漏
    llm_vision:
      enabled: true
      conf: 0.5
      scenes:
        feeding: "婴儿正在吃奶（奶瓶或母乳喂养）"
        crying: "婴儿哭闹、表情痛苦"
        changing: "正在换尿布"
        sleeping: "婴儿正在睡眠"

  recordings:
    motion:
      snapshot: false
      clip: false
    person:
      snapshot: true
      clip: false
    llm_crying:
      snapshot: true
      clip: true                      # 哭闹时保存视频片段
      clip_seconds: 30
    llm_feeding:
      snapshot: true
      clip: true
      clip_seconds: 20

cameras:
  - id: baby_room
    enabled: true
    stream_url: "rtsp://..."
    region: [0.05, 0.05, 0.95, 0.95] # 可选：裁剪婴儿床区域
```

### LLM 首次调试

首次配置 LLM 时，建议：

```bash
# 先降低阈值，用 -v 查看 LLM 实际返回的置信度
solo-surveillance -v

# 日志输出示例：
# [llm_vision] LLM 原始响应: {"feeding":0.0,"crying":0.0,"changing":0.12,"sleeping":0.0}
# [llm_vision] 场景识别结果 (frames=5): {}

# 如果 chaning 只有 0.12 但低于 conf:0.5 被过滤了，
# 说明场景描述不够准确，或需要调整 conf 值
```

根据日志调整 `conf` 和场景描述，直到达到满意的识别效果。
