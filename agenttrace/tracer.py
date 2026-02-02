"""JSONL trace writer — delegates I/O to the native backend (Rust or pure-Python fallback)."""

from __future__ import annotations

import json
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .config import get_root_dir
from .redaction import Redactor, RedactionConfig
from ._backend import NativeTraceWriter

_CURRENT_TRACER: ContextVar[Optional["Tracer"]] = ContextVar("current_tracer", default=None)

def get_current_tracer() -> Optional["Tracer"]:
    return _CURRENT_TRACER.get()

@dataclass
class Event:
    trace_id: str
    seq: int
    ts_unix_ns: int
    kind: str
    span_id: Optional[str]
    parent_span_id: Optional[str]
    level: str
    attrs: Dict[str, Any]
    payload: Dict[str, Any]


class Tracer:
    def __init__(
        self,
        trace_name: Optional[str] = None,
        project: Optional[str] = None,
        root_dir: Optional[Path] = None,
        redaction: Optional[RedactionConfig] = None,
    ):
        self.trace_name = trace_name or "trace"
        self.project = project
        self.trace_id = uuid.uuid4().hex
        self._seq = 0
        self._span_seq = 0
        self._redactor = Redactor(redaction)
        self._root = root_dir or get_root_dir()
        self._writer: Optional[NativeTraceWriter] = None
        self._token = None

    def __enter__(self) -> "Tracer":
        self.start()
        self._token = _CURRENT_TRACER.set(self)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.finish(error=exc)
        if self._token:
            _CURRENT_TRACER.reset(self._token)
            self._token = None

    def start(self) -> str:
        self._writer = NativeTraceWriter(self.trace_id, str(self._root))
        self.emit(
            "trace_start",
            payload={"trace_name": self.trace_name, "project": self.project},
        )
        return self.trace_id

    def finish(self, error: Exception | None = None) -> None:
        if error is None:
            self.emit("trace_end", payload={"status": "ok"})
        else:
            self.emit("trace_end", payload={"status": "error", "error": repr(error)})

        if self._writer:
            self._writer.finish()
            self._writer = None

    def new_span_id(self) -> str:
        self._span_seq += 1
        return f"s{self._span_seq}"

    def redact(self, value: Any) -> Any:
        return self._redactor.redact(value)

    def emit(
        self,
        kind: str,
        payload: Optional[Dict[str, Any]] = None,
        attrs: Optional[Dict[str, Any]] = None,
        level: str = "info",
        span_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
    ) -> Event:
        self._seq += 1
        safe_attrs = self._redactor.redact(attrs or {})
        safe_payload = self._redactor.redact(payload or {})
        ts_unix_ns = time.time_ns()

        if self._writer:
            self._writer.emit(
                self.trace_id,
                self._seq,
                ts_unix_ns,
                kind,
                span_id,
                parent_span_id,
                level,
                json.dumps(safe_attrs, ensure_ascii=False, default=str),
                json.dumps(safe_payload, ensure_ascii=False, default=str),
            )

        return Event(
            trace_id=self.trace_id,
            seq=self._seq,
            ts_unix_ns=ts_unix_ns,
            kind=kind,
            span_id=span_id,
            parent_span_id=parent_span_id,
            level=level,
            attrs=safe_attrs,
            payload=safe_payload,
        )

    def user_input(self, text: str, span_id: Optional[str] = None, parent_span_id: Optional[str] = None) -> Event:
        return self.emit("user_input", {"text": text}, span_id=span_id, parent_span_id=parent_span_id)

    def llm_request(self, payload: Dict[str, Any], span_id: Optional[str] = None, parent_span_id: Optional[str] = None) -> Event:
        return self.emit("llm_request", payload, span_id=span_id, parent_span_id=parent_span_id)

    def llm_response(self, payload: Dict[str, Any], span_id: Optional[str] = None, parent_span_id: Optional[str] = None) -> Event:
        return self.emit("llm_response", payload, span_id=span_id, parent_span_id=parent_span_id)

    def tool_call(self, payload: Dict[str, Any], span_id: Optional[str] = None, parent_span_id: Optional[str] = None) -> Event:
        return self.emit("tool_call", payload, span_id=span_id, parent_span_id=parent_span_id)

    def tool_result(self, payload: Dict[str, Any], span_id: Optional[str] = None, parent_span_id: Optional[str] = None) -> Event:
        return self.emit("tool_result", payload, span_id=span_id, parent_span_id=parent_span_id)

    def error(self, err: Exception, span_id: Optional[str] = None, parent_span_id: Optional[str] = None) -> Event:
        return self.emit("error", {"error": repr(err)}, level="error", span_id=span_id, parent_span_id=parent_span_id)


def trace(trace_name: str, project: Optional[str] = None, root_dir: Optional[Path] = None) -> Tracer:
    return Tracer(trace_name=trace_name, project=project, root_dir=root_dir)
