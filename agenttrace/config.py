"""Configuration helpers for AgentTrace."""

from __future__ import annotations

__all__ = ["get_root_dir", "get_store_full", "get_max_field_len", "get_redact_keys"]

import os
from pathlib import Path


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_root_dir() -> Path:
    env = os.getenv("AGENTTRACE_ROOT")
    if env:
        return Path(env)
    return Path.home() / ".agenttrace" / "traces"


def get_store_full() -> bool:
    return _parse_bool(os.getenv("AGENTTRACE_STORE_FULL"), default=False)


def get_max_field_len() -> int:
    raw = os.getenv("AGENTTRACE_MAX_FIELD_LEN")
    if not raw:
        return 512
    try:
        val = int(raw)
    except ValueError:
        return 512
    return max(val, 64)


def get_redact_keys() -> set[str]:
    raw = os.getenv("AGENTTRACE_REDACT", "")
    if not raw:
        return set()
    items = [item.strip().lower() for item in raw.split(",") if item.strip()]
    return set(items)
