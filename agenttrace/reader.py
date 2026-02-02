"""Reader for retrieving and parsing traces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from .storage import Storage


class TraceReader:
    def __init__(self, root: Optional[Path] = None):
        self.storage = Storage(db_path=root)

    def list_traces(self) -> List[Dict[str, Any]]:
        """List all traces with metadata, sorted by timestamp descending."""
        # Convert DB rows to expected format (if needed, but Storage.list_traces returns dicts)
        # We might need to map keys if they differ, but let's check Storage.
        # Storage returns: id, name, project, start_ts, end_ts, status, event_count
        # Previous reader returned: id, name, ts, event_count, project
        
        raw_traces = self.storage.list_traces()
        out = []
        for t in raw_traces:
            out.append({
                "id": t["id"],
                "name": t["name"] or "Untitled",
                "project": t["project"],
                "ts": t["start_ts"],
                "event_count": t["event_count"],
                "status": t["status"]
            })
        return out

    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get full trace details including all events."""
        raw_trace = self.storage.get_trace(trace_id)
        if not raw_trace:
            return None
            
        return {
            "id": raw_trace["id"],
            "trace_name": raw_trace["name"],
            "project": raw_trace["project"],
            "events": raw_trace["events"]
        }

    def iter_events(self, trace_id: str) -> Iterator[Dict[str, Any]]:
        """Lazy generator for events in a trace."""
        # For SQLite, getting all events is fast enough for now.
        # Ideally we'd cursor through them, but keeping it simple.
        trace = self.get_trace(trace_id)
        if not trace:
            return
        for evt in trace["events"]:
            yield evt
