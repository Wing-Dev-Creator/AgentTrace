"""Reader for retrieving and parsing traces — delegates to native backend."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from .config import get_root_dir
from ._backend import NativeTraceReader


class TraceReader:
    def __init__(self, root: Optional[Path] = None):
        self.root = root or get_root_dir()
        self._native = NativeTraceReader(str(self.root))

    def list_traces(self) -> List[Dict[str, Any]]:
        """List all traces with metadata, sorted by timestamp descending."""
        return self._native.list_traces()

    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get full trace details including all events."""
        try:
            events = self._native.get_events(trace_id)
        except (FileNotFoundError, RuntimeError):
            return None

        meta: Dict[str, Any] = {
            "id": trace_id,
            "trace_name": "Untitled",
            "project": None,
        }
        for evt in events:
            if evt.get("kind") == "trace_start":
                payload = evt.get("payload") or {}
                meta["trace_name"] = payload.get("trace_name") or "Untitled"
                meta["project"] = payload.get("project")
                break

        return {**meta, "events": events}

    def iter_events(self, trace_id: str) -> Iterator[Dict[str, Any]]:
        """Iterate over events in a trace."""
        try:
            events = self._native.get_events(trace_id)
        except (FileNotFoundError, RuntimeError):
            return
        yield from events
