"""Pure-Python fallback for when the native Rust extension is not available."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _strip_crc(line: str) -> str:
    """Remove CRC-32C tab suffix if present.

    The Rust writer appends ``\\t<8-char-hex>`` after each JSON line.
    This helper strips it so ``json.loads`` works on both old (plain)
    and new (CRC-suffixed) formats.
    """
    tab_pos = line.rfind("\t")
    if tab_pos != -1 and len(line) - tab_pos - 1 == 8:
        return line[:tab_pos]
    return line


class NativeTraceWriter:
    """Fallback writer that produces plain JSONL (no CRC)."""

    def __init__(self, trace_id: str, root: str) -> None:
        self._trace_id = trace_id
        trace_dir = Path(root) / trace_id
        trace_dir.mkdir(parents=True, exist_ok=True)
        self._path = trace_dir / "events.jsonl"
        self._file = self._path.open("a", encoding="utf-8")

    def emit(
        self,
        trace_id: str,
        seq: int,
        ts_unix_ns: int,
        kind: str,
        span_id: Optional[str],
        parent_span_id: Optional[str],
        level: str,
        attrs_json: str,
        payload_json: str,
    ) -> None:
        event = {
            "schema_version": 1,
            "trace_id": trace_id,
            "seq": seq,
            "ts_unix_ns": ts_unix_ns,
            "kind": kind,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "level": level,
            "attrs": json.loads(attrs_json),
            "payload": json.loads(payload_json),
        }
        self._file.write(json.dumps(event, separators=(",", ":")) + "\n")
        self._file.flush()

    def finish(self) -> None:
        if self._file and not self._file.closed:
            self._file.flush()
            self._file.close()


class NativeTraceReader:
    """Fallback reader that parses JSONL files, stripping CRC suffixes."""

    def __init__(self, root: str) -> None:
        self._root = Path(root)

    def list_traces(self) -> List[Dict[str, Any]]:
        if not self._root.exists():
            return []

        traces: List[Dict[str, Any]] = []
        for p in self._root.iterdir():
            if not p.is_dir():
                continue

            events_path = p / "events.jsonl"
            meta: Dict[str, Any] = {
                "id": p.name,
                "name": p.name,
                "project": None,
                "ts": p.stat().st_mtime,
                "event_count": 0,
            }

            if events_path.exists():
                try:
                    with events_path.open("r", encoding="utf-8") as f:
                        first_line = f.readline().strip()
                        if first_line:
                            data = json.loads(_strip_crc(first_line))
                            if data.get("kind") == "trace_start":
                                payload = data.get("payload") or {}
                                meta["name"] = payload.get("trace_name") or meta["name"]
                                meta["project"] = payload.get("project")
                                if "ts_unix_ns" in data:
                                    meta["ts"] = data["ts_unix_ns"] / 1e9

                        f.seek(0)
                        meta["event_count"] = sum(
                            1 for ln in f if ln.strip()
                        )
                except (OSError, json.JSONDecodeError, KeyError, ValueError):
                    pass

            traces.append(meta)

        return sorted(traces, key=lambda x: x["ts"], reverse=True)

    def get_events(self, trace_id: str) -> List[Dict[str, Any]]:
        path = self._root / trace_id / "events.jsonl"
        if not path.exists():
            raise FileNotFoundError(f"trace not found: {trace_id}")

        events: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                events.append(json.loads(_strip_crc(line)))
        return events
