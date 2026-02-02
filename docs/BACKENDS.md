# Storage & Backends

AgentTrace uses **JSONL** as its storage format, written by either:

1) **Native backend (Rust)** — preferred when `agenttrace_native` is available.
2) **Fallback backend (Python)** — used automatically if the native module is missing.

Both backends produce the same JSONL output and are fully interoperable. The reader accepts files written by either backend.

## Default storage path

```
~/.agenttrace/traces/<trace_id>/events.jsonl
```

Override via:

```
AGENTTRACE_ROOT=/custom/path
```

## Native backend (Rust)

- Module: `agenttrace_native` (built via `maturin develop --release`)
- Writes JSONL with CRC-32C suffix for integrity verification
- CRC uses hardware acceleration (SSE4.2 / ARM CRC) when available
- Reader detects and reports CRC mismatches on corrupted lines

## Fallback backend (Python)

- Module: `agenttrace/_native.py`
- Writes plain JSONL (no CRC)
- Reader accepts both CRC-suffixed and plain JSONL lines
- Activated automatically when the native extension is not installed

## How the fallback works

`agenttrace/_backend.py` handles the dispatch:

```python
try:
    from agenttrace_native import NativeTraceWriter, NativeTraceReader
except ImportError:
    from ._native import NativeTraceWriter, NativeTraceReader
```

The `Tracer` and `TraceReader` classes delegate all I/O to whichever backend is available. Application code does not need to change.
