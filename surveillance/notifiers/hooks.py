from __future__ import annotations

import json
import logging
import subprocess
import threading
from typing import Any

from surveillance.notifiers import Notifier

log = logging.getLogger(__name__)


class HooksNotifier(Notifier):
    """Execute external scripts on events via subprocess.

    Config section ``hooks`` (flat list, global)::

        hooks:
          - command: /path/to/notify.sh
          - command: /path/to/log.sh

    Every event fires all scripts. Each script receives ``--event-type`` and
    other metadata as CLI args and can decide whether to act.
    """

    def __init__(self, commands: list[str]) -> None:
        self._commands = commands
        log.info("Hooks notifier 已启用: %d 个脚本", len(commands))

    @classmethod
    def from_config(cls, raw: dict) -> HooksNotifier | None:
        hooks_cfg = raw.get("hooks")
        if not hooks_cfg:
            return None
        commands: list[str] = []
        for h in hooks_cfg:
            cmd = h.get("command") if isinstance(h, dict) else None
            if cmd:
                commands.append(str(cmd))
        if not commands:
            return None
        return cls(commands)

    def fire(self, event_type: str, data: dict) -> None:
        args = self._build_args(event_type, data)
        for cmd in self._commands:
            t = threading.Thread(
                target=self._run,
                args=(cmd, args),
                name=f"hook-{event_type}",
                daemon=True,
            )
            t.start()

    @staticmethod
    def _build_args(event_type: str, data: dict[str, Any]) -> list[str]:
        args = ["--event-type", event_type]
        for key in ("camera_id", "start_time", "end_time",
                     "snapshot_path", "clip_path"):
            val = data.get(key)
            if val:
                args.append(f"--{key.replace('_', '-')}")
                args.append(str(val))
        labels = data.get("labels")
        if labels:
            args.append("--labels")
            args.append(json.dumps(labels, ensure_ascii=False))
        return args

    @staticmethod
    def _run(command: str, args: list[str]) -> None:
        try:
            subprocess.run([command, *args], timeout=30)
        except subprocess.TimeoutExpired:
            log.warning("Hook 超时 (30s): %s", command)
        except Exception:
            log.exception("Hook 执行失败: %s", command)
