"""Redaction and sanitization utilities."""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from typing import Any

from .config import get_max_field_len, get_redact_keys, get_store_full

_DEFAULT_KEY_NAMES = {
    "authorization",
    "api_key",
    "apikey",
    "password",
    "token",
    "access_token",
    "secret",
    "openai_api_key",
    "anthropic_api_key",
    "bearer",
}

_DEFAULT_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"(?i)bearer\\s+[A-Za-z0-9\\-\\._~\\+/]+=*"),
    re.compile(r"(?i)authorization\\s*[:=]\\s*[^\\s,]+"),
    re.compile(r"(?i)api[_-]?key\\s*[:=]\\s*[^\\s,]+"),
    re.compile(r"(?i)password\\s*[:=]\\s*[^\\s,]+"),
]


@dataclass
class RedactionConfig:
    store_full: bool
    max_field_len: int
    extra_keys: set[str]


def load_redaction_config() -> RedactionConfig:
    return RedactionConfig(
        store_full=get_store_full(),
        max_field_len=get_max_field_len(),
        extra_keys=get_redact_keys(),
    )


class Redactor:
    def __init__(self, config: RedactionConfig | None = None) -> None:
        self.config = config or load_redaction_config()
        self._key_names = _DEFAULT_KEY_NAMES | self.config.extra_keys

    def redact(self, value: Any) -> Any:
        return self._sanitize(value, depth=0)

    def _sanitize(self, value: Any, depth: int) -> Any:
        if depth > 6:
            return "<depth_limit>"
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            return self._sanitize_str(value)
        if isinstance(value, bytes):
            if self.config.store_full:
                return base64.b64encode(value).decode("ascii")
            return f"<bytes:len={len(value)}>"
        if isinstance(value, (list, tuple)):
            return [self._sanitize(v, depth + 1) for v in value]
        if isinstance(value, dict):
            return self._sanitize_dict(value, depth + 1)
        if hasattr(value, "model_dump"):
            return self._sanitize(value.model_dump(), depth + 1)
        if hasattr(value, "__dict__"):
            return self._sanitize(vars(value), depth + 1)
        return self._sanitize_str(repr(value))

    def _sanitize_dict(self, value: dict[Any, Any], depth: int) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, val in value.items():
            key_str = str(key)
            if key_str.lower() in self._key_names:
                out[key_str] = "<redacted>"
            else:
                out[key_str] = self._sanitize(val, depth)
        return out

    def _sanitize_str(self, value: str) -> str:
        redacted = value
        for pattern in _DEFAULT_PATTERNS:
            redacted = pattern.sub("<redacted>", redacted)
        if not self.config.store_full and len(redacted) > self.config.max_field_len:
            redacted = redacted[: self.config.max_field_len] + "...(truncated)"
        return redacted
