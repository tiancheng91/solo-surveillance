# Home Assistant 集成

solo-surveillance 支持将事件推送到 Home Assistant 事件总线，用于自动化联动与通知。

## 配置

在 `config.yaml` 中添加：

```yaml
hass:
  enabled: true
  url: "http://homeassistant:8123"         # HA 服务器地址
  token: "${HASS_TOKEN}"                   # Long-Lived Access Token
  # event_prefix: "surveillance_"          # 可选：事件类型前缀
```

- `url` — Home Assistant 服务器地址（含端口）
- `token` — Long-Lived Access Token，在 HA 中生成：**个人资料 → 长期访问令牌**

> `token` 建议通过环境变量传入，避免明文写在配置文件中。事件名称固定以 `camera.` 为前缀（如 `camera.person`）。

## 事件类型

每个检测到的事件会 POST 到 `POST /api/events/{event_type}`，事件名称固定以 `camera.` 为前缀：

| 事件名称 | 触发条件 |
|----------|----------|
| `camera.motion` | 运动检测触发 |
| `camera.person` | YOLO 检测到人 |
| `camera.feeding` | LLM 识别到喂奶场景 |
| `camera.crying` | LLM 识别到婴儿哭闹 |
| 等 | 其他自定义场景名称 |

## 事件载荷

```json
{
  "camera_id": "xiaomi1",
  "event_type": "person",
  "start_time": "2026-05-12T14:05:30",
  "end_time": "2026-05-12T14:05:35",
  "labels": {"person": 0.95},
  "snapshot_path": "snapshots/140530_person.jpg",
  "clip_path": "clips/140530_person.mp4"
}
```

## Home Assistant 自动化示例

### 示例：有人移动 → Logbook 记录 + 开灯

```yaml
alias: "监控 - 有人移动"
triggers:
  - trigger: event
    event_type: camera.person
actions:
  # 在 HA Logbook 中留下记录（可在 日志 面板查看）
  - action: logbook.log
    data:
      name: "监控"
      message: "{{ trigger.event.data.camera_id }} 检测到人"
      entity_id: "binary_sensor.solo_camera_{{ trigger.event.data.camera_id }}"
  # 开灯（可选的，按需启用）
  - action: light.turn_on
    target:
      entity_id: light.porch
```

### 示例：人在状态传感器

创建一个 Template Binary Sensor，最后一个人体事件发生后保持 5 分钟"有人"状态，超过 5 分钟无事件则切换为"无人"。

**Step 1** — 在 `configuration.yaml` 中添加传感器定义：

```yaml
template:
  - binary_sensor:
      - name: "人在状态"
        unique_id: surveillance_person_present
        state: >
          {# 5分钟超时 #}
          {% set timeout = 300 %}
          {% set last = states('sensor.surveillance_last_event_time') | float(default=0) %}
          {{ last > 0 and (now().timestamp() - last) < timeout }}
        device_class: presence
```

**Step 2** — 添加自动化更新传感器时间戳：

```yaml
alias: "监控 - 更新人在时间戳"
triggers:
  - trigger: event
    event_type: camera.person
  - trigger: event
    event_type: camera.motion
actions:
  # 更新传感器时间戳为当前时间
  - action: sensor.surveillance_last_event_time
    data:
      state: "{{ now().timestamp() | int }}"
```

> 需要先在 HA 中创建 `sensor.surveillance_last_event_time` 辅助实体（开发者工具 → 辅助实体 → 创建 → 传感器），类型选"传感器"，单位留空。之后自动化会在每次检测到人/运动时更新它的值为当前时间戳，模板传感器据此判断 5 分钟内是否有人。

## 与其他集成方式对比

| 方式 | 依赖 | 复杂度 | 适用场景 |
|------|------|--------|----------|
| **HassClient（推荐）** | 零依赖 | 低 | 直接推送事件到 HA |
| **Hook 脚本** | 无 | 中 | 需要自定义逻辑（如调用多个 API） |

HassClient 适用于大多数场景。Hook 脚本适合需要额外逻辑处理的复杂场景。
