"""Reader for retrieving and parsing traces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from .storage import Storage
from ._backend import NativeTraceReader, NATIVE_AVAILABLE
from .config import get_root_dir


class TraceReader:
    def __init__(self, root: Optional[Path] = None):
        self.root = root or get_root_dir()
        self.storage = Storage(db_path=self.root)
        self.native = None
        if NATIVE_AVAILABLE:
            try:
                self.native = NativeTraceReader(str(self.root))
            except Exception:
                pass

    def list_traces(self) -> List[Dict[str, Any]]:
        """List all traces with metadata."""
        # SQLite is still better for metadata/listing because it has indexes
        # and stores end_ts/status which raw JSONL might lack without scanning.
        # But let's try to mix them or just use SQLite for listing for now.
        
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
        
        # 1. Try Rust Core (Fastest)
        if self.native:
            try:
                events = self.native.get_events(trace_id)
                if events:
                    # We need metadata (name, project) which isn't in events list easily
                    # without scanning. So fetch metadata from SQLite, events from Rust.
                    meta = self.storage.get_trace(trace_id)
                    if not meta:
                        return None
                        
                    return {
                        "id": trace_id,
                        "trace_name": meta.get("name"),
                        "project": meta.get("project"),
                        "events": events # From Rust!
                    }
            except Exception:
                # Fallback to SQLite if Rust fails (e.g. file missing but DB entry exists)
                pass

        # 2. Fallback to SQLite
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
        trace = self.get_trace(trace_id)
        if not trace:
            return
        for evt in trace["events"]:
            yield evt

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search for events matching the query."""
        # Search is still SQLite-only for now until we add search to Rust core
        return self.storage.search_events(query)
