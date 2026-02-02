# Replay

The `Replayer` class enables deterministic re-execution of recorded traces by providing recorded inputs and LLM responses instead of making live calls.

## Basic usage

```python
from agenttrace.replayer import Replayer, ReplayError

replayer = Replayer("trace-id-here")

# Get the next user input from the trace
user_input = replayer.consume_input()

# Get the next LLM response (skips the request, returns the response payload)
llm_response = replayer.expect_llm()

# Optionally verify the prompt matches expectations
llm_response = replayer.expect_llm(prompt_match="weather")
```

## API

### `Replayer(trace_id, reader=None)`

Loads a trace and initializes a cursor at the first event.

- `trace_id` — the trace to replay
- `reader` — optional `TraceReader` instance (uses default if not provided)
- Raises `ValueError` if the trace is not found.

### `next_event() -> Optional[dict]`

Peek at the next event without advancing the cursor. Returns `None` at end of trace.

### `advance()`

Move the cursor forward by one event.

### `consume_input() -> str`

Scans forward for the next `user_input` event and returns its `payload.text` value. Skips non-input events (logs, LLM calls, etc.).

Raises `ReplayError` if no more user input is found.

### `expect_llm(prompt_match=None) -> dict`

Scans forward for the next `llm_request` + `llm_response` pair and returns the response payload.

- `prompt_match` — optional string. If provided, the request payload is checked for this substring. Raises `ReplayError` on mismatch (divergence detection).

Raises `ReplayError` if the expected events are not found.

## Divergence detection

When `prompt_match` is provided to `expect_llm()`, the replayer verifies that the recorded LLM request contains the expected prompt. If it doesn't, a `ReplayError` is raised with a message describing the divergence.

This helps catch cases where code changes cause the agent to send different prompts than what was originally recorded.

## CLI replay

The CLI also supports trace replay:

```powershell
agenttrace replay <trace_id>
agenttrace replay <trace_id> --step          # pause between events
agenttrace replay <trace_id> --kind llm_request --kind tool_call  # filter by kind
agenttrace replay <trace_id> --span s1       # filter by span
```
