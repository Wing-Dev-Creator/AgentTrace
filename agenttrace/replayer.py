"""Replayer for deterministic execution."""

from __future__ import annotations

__all__ = ["Replayer", "ReplayError"]

from typing import Any, Dict, List, Optional

from .reader import TraceReader


class ReplayError(Exception):
    """Raised when replay diverges or fails."""
    pass


class Replayer:
    def __init__(self, trace_id: str, reader: Optional[TraceReader] = None):
        self.reader = reader or TraceReader()
        self.trace = self.reader.get_trace(trace_id)
        if not self.trace:
            raise ValueError(f"Trace {trace_id} not found")
        
        # Organize events for consumption
        self.events: List[Dict[str, Any]] = self.trace["events"]
        self._cursor = 0
        
    def next_event(self) -> Optional[Dict[str, Any]]:
        """Peek at the next event without advancing."""
        if self._cursor >= len(self.events):
            return None
        return self.events[self._cursor]

    def advance(self) -> None:
        """Move cursor forward."""
        self._cursor += 1

    def consume_input(self) -> str:
        """
        Finds the next 'user_input' event in the trace.
        Skips other events (like logs) until it finds one.
        """
        while self._cursor < len(self.events):
            evt = self.events[self._cursor]
            self._cursor += 1
            if evt.get("kind") == "user_input":
                payload = evt.get("payload") or {}
                text = payload.get("text")
                if text is not None:
                    return text
                raise ReplayError(f"user_input event at seq {evt.get('seq')} missing 'text' in payload")
        
        raise ReplayError("No more user input found in trace")

    def expect_llm(self, prompt_match: Optional[str] = None) -> Dict[str, Any]:
        """
        Expects the next significant event to be an 'llm_request' followed by 'llm_response'.
        Returns the response payload.
        """
        # 1. Find Request
        req = None
        while self._cursor < len(self.events):
            evt = self.events[self._cursor]
            self._cursor += 1
            if evt["kind"] == "llm_request":
                req = evt
                break
        
        if not req:
            raise ReplayError("Expected LLM request, found end of trace")

        # (Optional) Verify prompt matches (simple contains check)
        if prompt_match:
            # This is tricky because structure varies. 
            # Assuming payload has 'prompt' or 'messages'
            payload_str = str(req["payload"])
            if prompt_match not in payload_str:
                raise ReplayError(f"Replay divergence! Expected prompt containing '{prompt_match}', got: {payload_str}")

        # 2. Find Response
        resp = None
        while self._cursor < len(self.events):
            evt = self.events[self._cursor]
            self._cursor += 1
            if evt["kind"] == "llm_response":
                resp = evt
                break
                
        if not resp:
            raise ReplayError("Found LLM request but no response in trace")
            
        return resp["payload"]
