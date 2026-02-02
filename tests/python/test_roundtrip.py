"""Integration tests for the JSONL backend (pure-Python fallback)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from agenttrace import Tracer, trace
from agenttrace.reader import TraceReader
from agenttrace._native import NativeTraceWriter, NativeTraceReader, _strip_crc
from agenttrace._backend import NATIVE_AVAILABLE


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_tmp() -> Path:
    d = tempfile.mkdtemp(prefix="agenttrace_test_")
    return Path(d)


# ---------------------------------------------------------------------------
# _strip_crc
# ---------------------------------------------------------------------------

def test_strip_crc_with_suffix():
    line = '{"key":"value"}\ta1b2c3d4'
    assert _strip_crc(line) == '{"key":"value"}'


def test_strip_crc_without_suffix():
    line = '{"key":"value"}'
    assert _strip_crc(line) == '{"key":"value"}'


def test_strip_crc_tab_but_wrong_length():
    line = '{"key":"value"}\tshort'
    assert _strip_crc(line) == line  # not stripped — suffix isn't 8 chars


# ---------------------------------------------------------------------------
# NativeTraceWriter (fallback)
# ---------------------------------------------------------------------------

def test_fallback_writer_creates_dir_and_file():
    root = _make_tmp()
    w = NativeTraceWriter("trace-1", str(root))
    w.emit("trace-1", 1, 1000, "trace_start", None, None, "info", "{}", '{"trace_name":"demo"}')
    w.finish()

    events_path = root / "trace-1" / "events.jsonl"
    assert events_path.exists()

    lines = events_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1

    evt = json.loads(lines[0])
    assert evt["kind"] == "trace_start"
    assert evt["payload"]["trace_name"] == "demo"
    assert evt["trace_id"] == "trace-1"
    assert evt["seq"] == 1


def test_fallback_writer_multiple_events():
    root = _make_tmp()
    w = NativeTraceWriter("t2", str(root))
    w.emit("t2", 1, 100, "trace_start", None, None, "info", "{}", '{"trace_name":"x"}')
    w.emit("t2", 2, 200, "user_input", None, None, "info", "{}", '{"text":"hello"}')
    w.emit("t2", 3, 300, "trace_end", None, None, "info", "{}", '{"status":"ok"}')
    w.finish()

    lines = (root / "t2" / "events.jsonl").read_text().strip().splitlines()
    assert len(lines) == 3


# ---------------------------------------------------------------------------
# NativeTraceReader (fallback)
# ---------------------------------------------------------------------------

def test_fallback_reader_list_traces():
    root = _make_tmp()
    # Write two traces
    for name in ("alpha", "beta"):
        w = NativeTraceWriter(name, str(root))
        w.emit(name, 1, 100, "trace_start", None, None, "info", "{}", json.dumps({"trace_name": name}))
        w.emit(name, 2, 200, "trace_end", None, None, "info", "{}", '{"status":"ok"}')
        w.finish()

    reader = NativeTraceReader(str(root))
    traces = reader.list_traces()
    assert len(traces) == 2
    ids = {t["id"] for t in traces}
    assert ids == {"alpha", "beta"}
    for t in traces:
        assert t["event_count"] == 2


def test_fallback_reader_get_events():
    root = _make_tmp()
    w = NativeTraceWriter("t3", str(root))
    w.emit("t3", 1, 100, "trace_start", None, None, "info", "{}", '{"trace_name":"t3"}')
    w.emit("t3", 2, 200, "user_input", "s1", None, "info", "{}", '{"text":"hi"}')
    w.finish()

    reader = NativeTraceReader(str(root))
    events = reader.get_events("t3")
    assert len(events) == 2
    assert events[0]["kind"] == "trace_start"
    assert events[1]["span_id"] == "s1"
    assert events[1]["payload"]["text"] == "hi"


def test_fallback_reader_missing_trace():
    root = _make_tmp()
    reader = NativeTraceReader(str(root))
    try:
        reader.get_events("nonexistent")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass


def test_fallback_reader_reads_crc_lines():
    """Ensure the fallback reader can parse lines with CRC suffixes (written by Rust)."""
    root = _make_tmp()
    trace_dir = root / "crc-trace"
    trace_dir.mkdir(parents=True)
    events_path = trace_dir / "events.jsonl"

    event_json = json.dumps({
        "trace_id": "crc-trace", "seq": 1, "ts_unix_ns": 999,
        "kind": "trace_start", "span_id": None, "parent_span_id": None,
        "level": "info", "attrs": {}, "payload": {"trace_name": "crc-test"},
    })
    # Simulate Rust-written line with CRC suffix
    events_path.write_text(event_json + "\tdeadbeef\n", encoding="utf-8")

    reader = NativeTraceReader(str(root))
    events = reader.get_events("crc-trace")
    assert len(events) == 1
    assert events[0]["kind"] == "trace_start"
    assert events[0]["payload"]["trace_name"] == "crc-test"


# ---------------------------------------------------------------------------
# Full Tracer -> TraceReader roundtrip
# ---------------------------------------------------------------------------

def test_tracer_roundtrip():
    root = _make_tmp()

    with Tracer(trace_name="roundtrip", project="test-proj", root_dir=root) as t:
        t.user_input("what is 2+2?")
        t.llm_request({"model": "gpt-4", "prompt": "what is 2+2?"})
        t.llm_response({"text": "4"})
        trace_id = t.trace_id

    reader = TraceReader(root=root)

    # list_traces
    traces = reader.list_traces()
    assert len(traces) == 1
    assert traces[0]["id"] == trace_id
    assert traces[0]["name"] == "roundtrip"

    # get_trace
    full = reader.get_trace(trace_id)
    assert full is not None
    assert full["trace_name"] == "roundtrip"
    assert full["project"] == "test-proj"

    events = full["events"]
    # trace_start + user_input + llm_request + llm_response + trace_end = 5
    assert len(events) == 5
    kinds = [e["kind"] for e in events]
    assert kinds == ["trace_start", "user_input", "llm_request", "llm_response", "trace_end"]

    # trace_end should have status ok
    assert events[-1]["payload"]["status"] == "ok"


def test_tracer_roundtrip_with_error():
    root = _make_tmp()

    try:
        with Tracer(trace_name="err-test", root_dir=root) as t:
            t.user_input("trigger error")
            trace_id = t.trace_id
            raise ValueError("boom")
    except ValueError:
        pass

    reader = TraceReader(root=root)
    full = reader.get_trace(trace_id)
    assert full is not None
    events = full["events"]
    assert events[-1]["kind"] == "trace_end"
    assert events[-1]["payload"]["status"] == "error"
    assert "boom" in events[-1]["payload"]["error"]


def test_tracer_with_spans():
    root = _make_tmp()

    with Tracer(trace_name="span-test", root_dir=root) as t:
        span = t.new_span_id()
        t.tool_call({"tool": "calculator", "input": "2+2"}, span_id=span)
        t.tool_result({"output": "4"}, span_id=span)
        trace_id = t.trace_id

    reader = TraceReader(root=root)
    events = reader.get_trace(trace_id)["events"]
    tool_events = [e for e in events if e["kind"] in ("tool_call", "tool_result")]
    assert len(tool_events) == 2
    assert all(e["span_id"] == "s1" for e in tool_events)


def test_trace_convenience_function():
    root = _make_tmp()
    t = trace("convenience", root_dir=root)
    t.start()
    t.user_input("hello")
    t.finish()

    reader = TraceReader(root=root)
    traces = reader.list_traces()
    assert len(traces) == 1
    assert traces[0]["name"] == "convenience"


def test_iter_events():
    root = _make_tmp()

    with Tracer(trace_name="iter-test", root_dir=root) as t:
        t.user_input("a")
        t.user_input("b")
        trace_id = t.trace_id

    reader = TraceReader(root=root)
    events = list(reader.iter_events(trace_id))
    assert len(events) == 4  # trace_start + 2x user_input + trace_end


def test_backend_flag():
    """Verify NATIVE_AVAILABLE reflects the current state (should be False without Rust build)."""
    # In a pure-Python environment, native should not be available
    # This test documents the expected state — it will flip to True once Rust is compiled
    assert isinstance(NATIVE_AVAILABLE, bool)
