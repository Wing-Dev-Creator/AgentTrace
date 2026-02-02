# AgentTrace Architecture

AgentTrace is a Python-first telemetry recorder with an optional Rust native backend.

## Core idea

An agent run is recorded as a **timeline of structured events**.
Each event is a JSON object written to `events.jsonl` (optionally CRC-suffixed).

## Components

### Python SDK (`agenttrace/`)
- **Tracer** — writes events and handles redaction.
- **Reader** — loads traces through the native backend (or Python fallback).
- **Replayer** — replays recorded traces for deterministic re-execution.
- **CLI** — provides `ls / inspect / replay / diff / export / search / ui`.
- **Server** — FastAPI app serving the web UI and REST API.
- **Redaction** — strips API keys, secrets, and long fields before writing.
- **Pricing** — estimates LLM call costs from token usage.

### Auto-Instrumentation (`agenttrace/instrumentation/`)
- **OpenAI** — wraps `chat.completions.create` (sync, async, streaming).
- **Anthropic** — wraps `messages.create`.
- **LangChain** — proxy callback handler for chains, LLMs, tools, and retrievers.

### Native backend (Rust)
- **agenttrace-core** — event model, JSONL+CRC writing/reading, storage layout.
- **agenttrace-native** — PyO3 bindings exposing `NativeTraceWriter` and `NativeTraceReader`.

### Fallback backend (Python)
If the native module is missing, AgentTrace falls back to a pure-Python JSONL writer/reader in `agenttrace/_native.py`.

## Data flow

1. **Recording**
   User code -> `Tracer` -> Redactor -> Native writer (Rust) or fallback -> JSONL file

2. **Auto-Instrumentation**
   `instrument()` monkey-patches OpenAI/Anthropic/LangChain -> events emitted to active Tracer

3. **Viewing**
   CLI/UI -> `TraceReader` -> JSONL events -> output/visualization

4. **Replay**
   `Replayer` uses `TraceReader` to mock inputs and LLM responses

## Storage layout

```
~/.agenttrace/traces/<trace_id>/events.jsonl
```

CRC suffix (native backend only):

```
<json>\t<crc32c>
```

## Web UI

The server (`agenttrace/server.py`) exposes:
- `GET /` — serves the timeline UI
- `GET /api/traces` — lists all traces
- `GET /api/traces/{id}` — returns events for a trace
- `GET /api/search?q=...` — full-text search across events
