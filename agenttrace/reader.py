"""Reader for retrieving and parsing traces."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from ._backend import NativeTraceReader
from .config import get_root_dir


class TraceReader:
    def __init__(self, root: Optional[Path] = None):
        self.root = root or get_root_dir()
        self._reader = NativeTraceReader(str(self.root))

    def list_traces(self) -> List[Dict[str, Any]]:
        """List all traces with metadata."""
        return self._reader.list_traces()

    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get full trace details including all events."""
        try:
            events = self._reader.get_events(trace_id)
        except FileNotFoundError:
            return None

        # Extract metadata from the trace_start event if available
        trace_name = trace_id
        project = None
        if events:
            first = events[0]
            if first.get("kind") == "trace_start":
                payload = first.get("payload") or {}
                trace_name = payload.get("trace_name") or trace_id
                project = payload.get("project")

        return {
            "id": trace_id,
            "trace_name": trace_name,
            "project": project,
            "events": events,
        }

    def iter_events(self, trace_id: str) -> Iterator[Dict[str, Any]]:
        """Lazy generator for events in a trace."""
        trace = self.get_trace(trace_id)
        if not trace:
            return
        for evt in trace["events"]:
            yield evt

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search for events matching the query across all traces.

        Performs a simple substring match on event payloads.
        """
        results: List[Dict[str, Any]] = []
        for trace_meta in self.list_traces():
            try:
                events = self._reader.get_events(trace_meta["id"])
            except FileNotFoundError:
                continue
            for evt in events:
                payload_str = str(evt.get("payload", ""))
                attrs_str = str(evt.get("attrs", ""))
                if query in payload_str or query in attrs_str:
                    evt["trace_name"] = trace_meta.get("name", "")
                    results.append(evt)
        return results
