"""Simple JSONL trace writer (MVP scaffold)."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .config import get_root_dir
from .redaction import Redactor, RedactionConfig
from .storage import Storage


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
        self._storage = Storage(db_path=root_dir)

    def __enter__(self) -> "Tracer":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.finish(error=exc)

    def start(self) -> str:
        self._storage.create_trace(
            trace_id=self.trace_id, 
            name=self.trace_name, 
            project=self.project,
            start_ts=time.time()
        )
        self.emit(
            "trace_start",
            payload={"trace_name": self.trace_name, "project": self.project},
        )
        return self.trace_id

    def finish(self, error: Exception | None = None) -> None:
        status = "ok"
        if error is None:
            self.emit("trace_end", payload={"status": "ok"})
        else:
            status = "error"
            self.emit("trace_end", payload={"status": "error", "error": repr(error)})
            
        self._storage.update_trace(
            trace_id=self.trace_id,
            end_ts=time.time(),
            status=status
        )

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
        
        self._storage.add_event(
            trace_id=self.trace_id,
            seq=self._seq,
            ts_unix_ns=ts_unix_ns,
            kind=kind,
            level=level,
            attrs=safe_attrs,
            payload=safe_payload,
            span_id=span_id,
            parent_span_id=parent_span_id
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
