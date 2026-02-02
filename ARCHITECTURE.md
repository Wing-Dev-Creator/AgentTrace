# AgentTrace Architecture

AgentTrace is a hybrid Python/Rust observability platform for AI agents.

## Directory Structure

```text
C:\Users\Wing\Dev\Rust\AgentTrace\
├── agenttrace/           # Python SDK & CLI (User-facing)
│   ├── tracer.py         # Main recording API
│   ├── replayer.py       # Deterministic replay engine
│   ├── server.py         # FastAPI backend for UI
│   ├── web/              # Single-page React-style UI
│   └── storage.py        # SQLite storage backend
├── crates/               # Rust Components (High-performance)
│   └── agenttrace-core/  # Core library (Event types, CRC, Storage IO)
├── examples/             # Usage examples
└── pyproject.toml        # Python project config
```

## Components

### 1. Python SDK (`agenttrace/`)
The primary interface for users.
*   **Tracer:** Instruments code to capture `user_input`, `llm_request`, `tool_call`.
*   **Storage:** Currently uses SQLite (`agenttrace.db`) with WAL mode for fast concurrent writes.
*   **UI:** A local visualization tool (`agenttrace ui`) built with FastAPI + raw HTML/JS.

### 2. Rust Core (`crates/agenttrace-core/`)
A standalone library for high-performance telemetry handling.
*   **Role:** Defines the canonical event structure and binary/structured file formats.
*   **Format:** Supports a custom JSONL+CRC32C format for data integrity.
*   **Future:** Will be bound to Python via PyO3 to replace the Python-side storage layer for extreme throughput.

## Data Flow

1.  **Recording:** User Code -> `Tracer` (Python) -> `Storage` (SQLite)
2.  **Viewing:** User -> CLI/Browser -> `TraceReader` -> SQLite -> JSON Output
3.  **Replaying:** User -> `Replayer` -> SQLite -> Mocked I/O

## Development

*   **Python:** `pip install -e .` (Requires Python 3.9+)
*   **Rust:** `cargo build` (Requires Rust 1.70+)

```