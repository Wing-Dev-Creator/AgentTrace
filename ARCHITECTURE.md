# AgentTrace Architecture

AgentTrace is a hybrid Python/Rust observability platform for AI agents.

## Directory Structure

```text
C:\Users\Wing\Dev\Rust\AgentTrace\
├── agenttrace/           # Python SDK & CLI (User-facing)
│   ├── tracer.py         # Main recording API
│   ├── replayer.py       # Deterministic replay engine (uses TraceReader)
│   ├── server.py         # FastAPI backend for UI
│   ├── web/              # Single-page React-style UI
│   ├── reader.py         # JSONL reader (native or fallback)
│   ├── _backend.py       # Native fallback dispatcher
│   ├── _native.py        # Pure-Python JSONL fallback
│   └── storage.py        # Experimental SQLite backend (not default)
├── crates/               # Rust Components (High-performance)
│   └── agenttrace-core/  # Core library (Event types, CRC, Storage IO)
│   └── agenttrace-native/# PyO3 bindings (agenttrace_native)
├── examples/             # Usage examples
└── pyproject.toml        # Python project config
```

## Components

### 1. Python SDK (`agenttrace/`)
The primary interface for users.
*   **Tracer:** Instruments code to capture `user_input`, `llm_request`, `tool_call`.
*   **Storage (MVP):** JSONL + optional CRC, written by the native backend (Rust) or the pure-Python fallback.
*   **Reader:** Uses the native backend when available, falls back to JSONL parsing in Python.
*   **UI:** A local visualization tool (`agenttrace ui`) built with FastAPI + raw HTML/JS.
*   **SQLite:** Present as an experimental backend (`storage.py`) but not wired into the default path.

### 2. Rust Core (`crates/agenttrace-core/`)
A standalone library for high-performance telemetry handling.
*   **Role:** Defines the canonical event structure and binary/structured file formats.
*   **Format:** Supports a custom JSONL+CRC32C format for data integrity.
*   **Python Bridge:** Bound via PyO3 in `agenttrace-native` (module `agenttrace_native`).

## Data Flow

1.  **Recording:** User Code -> `Tracer` (Python) -> Native writer (Rust or fallback) -> JSONL (+ optional CRC)
2.  **Viewing:** User -> CLI/Browser -> `TraceReader` -> JSONL -> JSON Output
3.  **Replaying:** User -> `Replayer` -> `TraceReader` -> Mocked I/O

## Development

*   **Python:** `pip install -e .` (Requires Python 3.9+)
*   **Rust:** `cargo build` (Requires Rust 1.70+)

```
