"""Tests for the Replayer module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from agenttrace import Tracer
from agenttrace.reader import TraceReader
from agenttrace.replayer import Replayer, ReplayError


def _make_tmp() -> Path:
    return Path(tempfile.mkdtemp(prefix="agenttrace_replay_"))


def _make_trace_with_conversation(root: Path) -> str:
    with Tracer(trace_name="replay-test", project="test", root_dir=root) as t:
        t.user_input("What is 2+2?")
        t.llm_request({"model": "gpt-4", "prompt": "What is 2+2?"})
        t.llm_response({"text": "4"})
        t.user_input("Thanks!")
        return t.trace_id


def test_replayer_init():
    root = _make_tmp()
    trace_id = _make_trace_with_conversation(root)
    reader = TraceReader(root=root)
    replayer = Replayer(trace_id, reader=reader)
    assert replayer.trace is not None
    assert len(replayer.events) > 0


def test_replayer_not_found():
    root = _make_tmp()
    reader = TraceReader(root=root)
    with pytest.raises(ValueError, match="not found"):
        Replayer("nonexistent", reader=reader)


def test_replayer_consume_input():
    root = _make_tmp()
    trace_id = _make_trace_with_conversation(root)
    reader = TraceReader(root=root)
    replayer = Replayer(trace_id, reader=reader)

    text = replayer.consume_input()
    assert text == "What is 2+2?"


def test_replayer_expect_llm():
    root = _make_tmp()
    trace_id = _make_trace_with_conversation(root)
    reader = TraceReader(root=root)
    replayer = Replayer(trace_id, reader=reader)

    # Skip past user_input to get to llm_request/response
    replayer.consume_input()
    response = replayer.expect_llm()
    assert response["text"] == "4"


def test_replayer_expect_llm_with_match():
    root = _make_tmp()
    trace_id = _make_trace_with_conversation(root)
    reader = TraceReader(root=root)
    replayer = Replayer(trace_id, reader=reader)

    replayer.consume_input()
    response = replayer.expect_llm(prompt_match="2+2")
    assert response["text"] == "4"


def test_replayer_expect_llm_divergence():
    root = _make_tmp()
    trace_id = _make_trace_with_conversation(root)
    reader = TraceReader(root=root)
    replayer = Replayer(trace_id, reader=reader)

    replayer.consume_input()
    with pytest.raises(ReplayError, match="divergence"):
        replayer.expect_llm(prompt_match="completely different prompt")


def test_replayer_consume_all_inputs():
    root = _make_tmp()
    trace_id = _make_trace_with_conversation(root)
    reader = TraceReader(root=root)
    replayer = Replayer(trace_id, reader=reader)

    first = replayer.consume_input()
    assert first == "What is 2+2?"

    # Skip llm pair
    replayer.expect_llm()

    second = replayer.consume_input()
    assert second == "Thanks!"


def test_replayer_no_more_input():
    root = _make_tmp()
    trace_id = _make_trace_with_conversation(root)
    reader = TraceReader(root=root)
    replayer = Replayer(trace_id, reader=reader)

    replayer.consume_input()
    replayer.expect_llm()
    replayer.consume_input()

    with pytest.raises(ReplayError, match="No more user input"):
        replayer.consume_input()


def test_replayer_next_event_and_advance():
    root = _make_tmp()
    trace_id = _make_trace_with_conversation(root)
    reader = TraceReader(root=root)
    replayer = Replayer(trace_id, reader=reader)

    first = replayer.next_event()
    assert first is not None
    # next_event should not advance
    assert replayer.next_event() == first

    replayer.advance()
    second = replayer.next_event()
    assert second != first
