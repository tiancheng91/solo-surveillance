#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# 事件日志/通知脚本 — Hook 示例
# ═══════════════════════════════════════════════════════════════
#
# 配置方式 (config.yaml):
#
#   hooks:
#     - command: scripts/event_logger.sh
#
# 所有事件类型（motion / person / feeding / crying ...）都会调用此脚本，
# 根据 --event-type 参数自行判断是否处理。
#
# 自定义脚本时复制此文件，按需修改 ##### 用户自定义区域 ##### 即可。
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

# ── 解析参数 ──────────────────────────────────────────────────
# 以下参数由 HooksNotifier 按顺序传入
while [[ $# -gt 0 ]]; do
    case "$1" in
        --event-type)      EVENT_TYPE="$2";       shift 2 ;;
        --camera-id)       CAMERA_ID="$2";        shift 2 ;;
        --start-time)      START_TIME="$2";       shift 2 ;;
        --end-time)        END_TIME="$2";         shift 2 ;;
        --snapshot-path)   SNAPSHOT_PATH="$2";    shift 2 ;;
        --clip-path)       CLIP_PATH="$2";        shift 2 ;;
        --labels)          LABELS="$2";           shift 2 ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
done

# ── 日志输出（所有事件都会打印）────────────────────────────────
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
echo "[${TIMESTAMP}] event=${EVENT_TYPE} camera=${CAMERA_ID}"
echo "  start:    ${START_TIME:-"-"}"
echo "  end:      ${END_TIME:-"-"}"
echo "  labels:   ${LABELS:-"-"}"
echo "  snapshot: ${SNAPSHOT_PATH:-"-"}"
echo "  clip:     ${CLIP_PATH:-"-"}"
echo "---"

# ═══════════════════════════════════════════════════════════════
# ##### 用户自定义区域 — 按需取消注释或修改 #####
# ═══════════════════════════════════════════════════════════════

# ── 示例 1：仅处理 person 事件，其他跳过 ──────────────────────
# if [ "${EVENT_TYPE:-}" != "person" ]; then
#     exit 0
# fi

# ── 示例 2：curl 推送自定义 API ───────────────────────────────
# curl -s -X POST "https://your-api.example.com/alert" \
#   -H "Content-Type: application/json" \
#   -d "{
#     \"camera\": \"${CAMERA_ID}\",
#     \"event\":  \"${EVENT_TYPE}\",
#     \"time\":   \"${START_TIME}\",
#     \"labels\": ${LABELS:-null}
#   }"

# ── 示例 3：macOS 桌面通知 ───────────────────────────────────
# osascript -e "display notification \"${CAMERA_ID} — ${EVENT_TYPE}\" with title \"NVR\""

# ── 示例 4：从视频片段截取一帧作为告警图 ────────────────────
# if [ -n "${CLIP_PATH:-}" ]; then
#     ffmpeg -y -i "${CLIP_PATH}" -vframes 1 "/tmp/alert_${CAMERA_ID}.jpg" 2>/dev/null
# fi

# ── 示例 5：Pushover 推送 ────────────────────────────────────
# curl -s -F "token=APP_TOKEN" -F "user=USER_KEY" \
#   -F "title=NVR" \
#   -F "message=${CAMERA_ID} — ${EVENT_TYPE}" \
#   https://api.pushover.net/1/messages.json
