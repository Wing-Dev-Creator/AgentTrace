"""Experimental SQLite storage backend for AgentTrace (not default)."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Iterator

from .config import get_root_dir


def _adapt_dict(d: Dict[str, Any]) -> str:
    return json.dumps(d)


def _convert_dict(s: bytes) -> Dict[str, Any]:
    return json.loads(s)


sqlite3.register_adapter(dict, _adapt_dict)
sqlite3.register_converter("JSON", _convert_dict)


class Storage:
    def __init__(self, db_path: Optional[Path] = None):
        self.root = db_path or get_root_dir()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "agenttrace.db"
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            str(self.db_path), 
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        # Enable WAL for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        try:
            with conn:
                conn.execute("""
                CREATE TABLE IF NOT EXISTS traces (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    project TEXT,
                    start_ts REAL,
                    end_ts REAL,
                    status TEXT,
                    event_count INTEGER DEFAULT 0
                )
                """)
                conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id TEXT,
                    seq INTEGER,
                    ts_unix_ns INTEGER,
                    kind TEXT,
                    span_id TEXT,
                    parent_span_id TEXT,
                    level TEXT,
                    attrs JSON,
                    payload JSON,
                    FOREIGN KEY(trace_id) REFERENCES traces(id)
                )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_events_trace_id ON events(trace_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_traces_start_ts ON traces(start_ts DESC)")
        finally:
            conn.close()

    def create_trace(self, trace_id: str, name: str, project: Optional[str], start_ts: float) -> None:
        conn = self._get_conn()
        with conn:
            conn.execute(
                "INSERT INTO traces (id, name, project, start_ts, status) VALUES (?, ?, ?, ?, ?)",
                (trace_id, name, project, start_ts, "running"),
            )
        conn.close()

    def update_trace(self, trace_id: str, end_ts: float, status: str) -> None:
        conn = self._get_conn()
        with conn:
            conn.execute(
                "UPDATE traces SET end_ts = ?, status = ? WHERE id = ?",
                (end_ts, status, trace_id),
            )
        conn.close()

    def add_event(
        self,
        trace_id: str,
        seq: int,
        ts_unix_ns: int,
        kind: str,
        level: str,
        attrs: Dict[str, Any],
        payload: Dict[str, Any],
        span_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
    ) -> None:
        conn = self._get_conn()
        with conn:
            conn.execute(
                """
                INSERT INTO events (trace_id, seq, ts_unix_ns, kind, span_id, parent_span_id, level, attrs, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (trace_id, seq, ts_unix_ns, kind, span_id, parent_span_id, level, attrs, payload),
            )
            # Increment event count
            conn.execute("UPDATE traces SET event_count = event_count + 1 WHERE id = ?", (trace_id,))
        conn.close()

    def list_traces(self, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM traces ORDER BY start_ts DESC LIMIT ?", (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            # Get trace metadata
            row = conn.execute("SELECT * FROM traces WHERE id = ?", (trace_id,)).fetchone()
            if not row:
                return None
            
            trace_data = dict(row)
            
            # Get events
            events_cursor = conn.execute(
                "SELECT * FROM events WHERE trace_id = ? ORDER BY seq ASC", (trace_id,)
            )
            events = [dict(r) for r in events_cursor.fetchall()]
            
            trace_data["events"] = events
            return trace_data
        finally:
            conn.close()

    def search_events(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            # Simple LIKE search on payload/attrs for MVP
            # In production, use FTS5
            sql = """
                SELECT e.*, t.name as trace_name 
                FROM events e
                JOIN traces t ON e.trace_id = t.id
                WHERE json_extract(e.payload, '$') LIKE ? 
                   OR json_extract(e.attrs, '$') LIKE ?
                ORDER BY e.ts_unix_ns DESC
                LIMIT ?
            """
            wildcard = f"%{query}%"
            cursor = conn.execute(sql, (wildcard, wildcard, limit))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
