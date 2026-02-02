# Testing

## Python tests

The Python test suite lives in `tests/python/`.

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

Run Rust tests (workspace):

```powershell
cargo test
```

To run only the core crate:

```powershell
cargo test -p agenttrace-core
```
