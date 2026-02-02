# Storage & Backends

AgentTrace uses **JSONL** as the MVP storage format, written by either:

1) **Native backend (Rust)** — preferred when `agenttrace_native` is available.  
2) **Fallback backend (Python)** — used automatically if the native module is missing.

## Default storage path

```
~/.agenttrace/traces/<trace_id>/events.jsonl
```

Override via:

```
AGENTTRACE_ROOT=/custom/path
```

## Native backend (Rust)

- Module: `agenttrace_native`
- Built via `maturin develop --release`
- Writes JSONL with optional CRC32C suffix for integrity

## Fallback backend (Python)

- Module: `agenttrace/_native.py`
- Writes plain JSONL (no CRC)
- Reader accepts both CRC‑suffixed and plain JSONL lines

## SQLite backend (experimental)

`agenttrace/storage.py` contains a SQLite implementation for future search/analytics.
It is **not** wired into the default tracer/reader path yet.

If/when it becomes the default, the CLI and UI will be updated to support DB queries.
