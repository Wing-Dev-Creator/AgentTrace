# AgentTrace Architecture (Current)

AgentTrace is a Python‑first telemetry recorder with an optional Rust native backend.

## Core idea

An agent run is recorded as a **timeline of structured events**.  
Each event is a JSON object written to `events.jsonl` (optionally CRC‑suffixed).

## Components

### Python SDK (`agenttrace/`)
- **Tracer** writes events and handles redaction.
- **Reader** loads traces through the native backend (or Python fallback).
- **CLI** provides `ls / inspect / replay / diff / export`.
- **UI** runs locally via FastAPI and static HTML.

### Native backend (Rust)
- **agenttrace-core**: event model + JSONL+CRC writing/reading.
- **agenttrace-native**: PyO3 bindings exposing `NativeTraceWriter` and `NativeTraceReader`.

### Fallback backend (Python)
If the native module is missing, AgentTrace falls back to a pure‑Python JSONL writer/reader.

## Data flow

1) **Recording**  
User code → `Tracer` → Native writer (Rust) or fallback → JSONL file

2) **Viewing**  
CLI/UI → `TraceReader` → JSONL events → output/visualization

3) **Replay**  
`Replayer` uses `TraceReader` to mock inputs and LLM responses

## Storage layout

```
~/.agenttrace/traces/<trace_id>/events.jsonl
```

CRC suffix is optional:

```
<json>\t<crc32c>
```

## Experimental: SQLite backend

`agenttrace/storage.py` contains a SQLite implementation for future search/analytics.  
It is not wired into the default path yet.
