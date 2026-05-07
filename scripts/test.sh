#!/usr/bin/env bash
# 人检测事件 hook 示例脚本
# 安装: chmod +x scripts/on_person.sh
# 然后在 config.yaml 的 hooks.person 中引用此脚本

set -euo pipefail

# ── 解析参数 ──────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --camera-id)      CAMERA_ID="$2";       shift 2 ;;
        --event-type)     EVENT_TYPE="$2";       shift 2 ;;
        --start-time)     START_TIME="$2";       shift 2 ;;
        --end-time)       END_TIME="$2";         shift 2 ;;
        --snapshot-path)  SNAPSHOT_PATH="$2";    shift 2 ;;
        --clip-path)      CLIP_PATH="$2";        shift 2 ;;
        --labels)         LABELS="$2";           shift 2 ;;
        *) echo "unknown: $1"; exit 1 ;;
    esac
done

echo "[hook] camera=$CAMERA_ID event=$EVENT_TYPE at $START_TIME"
echo "       snapshot=$SNAPSHOT_PATH"
echo "       clip=$CLIP_PATH"
echo "       labels=$LABELS"

# ── 在这里添加你的自定义动作 ──────────────────────────────
# 例如:
#   curl -s -X POST "https://api.xxxx.com/alert" \
#     -H "Content-Type: application/json" \
#     -d "{\"camera\": \"$CAMERA_ID\", \"time\": \"$START_TIME\"}"
#
#   osascript -e "display notification \"$CAMERA_ID 检测到人\" with title \"NVR\""
#
#   ffmpeg -i "$CLIP_PATH" -vframes 1 /tmp/alert.jpg
