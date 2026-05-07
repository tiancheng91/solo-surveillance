from __future__ import annotations

import json
import logging
import subprocess
import threading
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class HookConfig:
    command: str


class HooksManager:
    """读取配置中的 hooks 段，触发时通过子进程调用外部脚本。"""

    def __init__(self, hooks_cfg: dict[str, list[dict]] | None) -> None:
        self._hooks: dict[str, list[HookConfig]] = {}
        if not hooks_cfg:
            return
        for event_type, raw_list in hooks_cfg.items():
            if not isinstance(raw_list, list):
                continue
            cfgs = [
                HookConfig(command=h["command"])
                for h in raw_list
                if isinstance(h, dict) and "command" in h
            ]
            if cfgs:
                self._hooks[event_type] = cfgs

    def fire(self, event_type: str, data: dict[str, Any]) -> None:
        """为 event_type 触发所有已注册脚本（每个脚本在独立 daemon 线程中执行）。"""
        hooks = self._hooks.get(event_type)
        if not hooks:
            return

        args = self._build_args(data)
        for hook in hooks:
            t = threading.Thread(
                target=self._run,
                args=(hook.command, args),
                name=f"hook-{event_type}",
                daemon=True,
            )
            t.start()

    # ── 内部 ──────────────────────────────────────────────────────

    def _build_args(self, data: dict[str, Any]) -> list[str]:
        args: list[str] = []
        for key in ("camera_id", "event_type", "start_time", "end_time",
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

    def _run(self, command: str, args: list[str]) -> None:
        try:
            subprocess.run(
                [command, *args],
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            log.warning("Hook 超时 (30s): %s", command)
        except Exception:
            log.exception("Hook 执行失败: %s", command)
