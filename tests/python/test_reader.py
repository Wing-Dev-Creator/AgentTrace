"""Tests for the TraceReader (high-level reader using backend)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from agenttrace.reader import TraceReader
from agenttrace._native import NativeTraceWriter


def _make_tmp() -> Path:
    return Path(tempfile.mkdtemp(prefix="agenttrace_reader_"))


def _write_trace(root: Path, trace_id: str, name: str, project: str = None, events: int = 0):
    """Helper to write a trace with events."""
    w = NativeTraceWriter(trace_id, str(root))
    w.emit(trace_id, 1, 100, "trace_start", None, None, "info", "{}",
           json.dumps({"trace_name": name, "project": project}))
    for i in range(events):
        w.emit(trace_id, i + 2, 200 + i, "user_input", None, None, "info", "{}",
               json.dumps({"text": f"msg-{i}"}))
    w.emit(trace_id, events + 2, 999, "trace_end", None, None, "info", "{}",
           json.dumps({"status": "ok"}))
    w.finish()


def test_reader_list_traces():
    root = _make_tmp()
    _write_trace(root, "t1", "alpha")
    _write_trace(root, "t2", "beta")

    reader = TraceReader(root=root)
    traces = reader.list_traces()
    assert len(traces) == 2
    ids = {t["id"] for t in traces}
    assert ids == {"t1", "t2"}


def test_reader_get_trace():
    root = _make_tmp()
    _write_trace(root, "t1", "mytest", project="proj1", events=2)

    reader = TraceReader(root=root)
    trace = reader.get_trace("t1")
    assert trace is not None
    assert trace["trace_name"] == "mytest"
    assert trace["project"] == "proj1"
    # trace_start + 2 user_input + trace_end = 4
    assert len(trace["events"]) == 4


def test_reader_get_trace_not_found():
    root = _make_tmp()
    reader = TraceReader(root=root)
    assert reader.get_trace("nonexistent") is None


def test_reader_iter_events():
    root = _make_tmp()
    _write_trace(root, "t1", "iter", events=3)

    reader = TraceReader(root=root)
    events = list(reader.iter_events("t1"))
    assert len(events) == 5  # trace_start + 3 user_input + trace_end


def test_reader_iter_events_missing():
    root = _make_tmp()
    reader = TraceReader(root=root)
    events = list(reader.iter_events("missing"))
    assert events == []


def test_reader_search():
    root = _make_tmp()
    _write_trace(root, "t1", "searchtest", events=2)

    reader = TraceReader(root=root)
    results = reader.search("msg-1")
    assert len(results) >= 1
    assert any("msg-1" in str(r.get("payload", "")) for r in results)


def test_reader_search_no_results():
    root = _make_tmp()
    _write_trace(root, "t1", "searchtest", events=1)

    reader = TraceReader(root=root)
    results = reader.search("nonexistent_query_xyz")
    assert results == []
