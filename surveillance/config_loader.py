from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def expand_env_str(value: str) -> str:
    def repl(m: re.Match[str]) -> str:
        return os.environ.get(m.group(1), "")

    return _ENV_PATTERN.sub(repl, value)


def expand_env(obj: Any) -> Any:
    if isinstance(obj, str):
        return expand_env_str(obj)
    if isinstance(obj, dict):
        return {k: expand_env(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [expand_env(v) for v in obj]
    return obj


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"配置文件不存在: {p}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("配置文件根节点必须是 mapping")
    return expand_env(raw)


def camera_effective_config(global_cfg: dict[str, Any], camera: dict[str, Any]) -> dict[str, Any]:
    """合并 defaults 与单路 cameras[] 项。"""
    defaults = global_cfg.get("defaults") or {}
    merged = deep_merge(defaults, camera)
    return merged
