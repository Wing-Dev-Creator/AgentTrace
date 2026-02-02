# Testing

AgentTrace has 64 Python tests and 6 Rust tests.

## Python tests

The Python test suite lives in `tests/python/` and covers:

- `test_roundtrip.py` — end-to-end tracer write/read cycles
- `test_reader.py` — TraceReader listing, loading, search
- `test_redaction.py` — secret scrubbing, truncation, depth limits
- `test_config.py` — environment variable parsing, defaults
- `test_cli.py` — CLI subcommands (ls, inspect, export, search)
- `test_replayer.py` — replay cursor, input consumption, divergence detection

Install pytest if needed:

```powershell
pip install pytest
```

Run tests:

```powershell
python -m pytest tests/python
```

## Native extension (optional)

Build the Rust extension with maturin:

```powershell
maturin develop --release
```

Smoke test:

```powershell
python -c "import agenttrace_native; print(agenttrace_native.NativeTraceWriter)"
```

## Rust tests

Run all Rust tests (workspace):

```powershell
cargo test
```

Run only the core crate:

```powershell
cargo test -p agenttrace-core
```

The Rust tests cover CRC calculation, writer output, reader verification, corruption detection, legacy (no-CRC) support, and trace listing.
