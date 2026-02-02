# AgentTrace CLI

`agenttrace` provides local inspection, replay, and export tools.

## Commands

### List traces

```powershell
agenttrace ls
```

### Inspect a trace

```powershell
agenttrace inspect <trace_id>
```

### Replay a trace (timeline)

```powershell
agenttrace replay <trace_id>
```

Options:

```powershell
agenttrace replay <trace_id> --step
agenttrace replay <trace_id> --kind llm_request --kind tool_call
agenttrace replay <trace_id> --span s1
```

Notes:

- `replay` is a **timeline view** (read‑only) today.
- Deterministic re‑execution is tracked in `agenttrace.replayer` and will be
  expanded in a future release.

### Diff two traces

```powershell
agenttrace diff <trace_a> <trace_b>
```

### Export a trace

```powershell
agenttrace export <trace_id> --out trace.json
```

### Launch the UI

```powershell
pip install -e .[ui]
agenttrace ui --port 8000
```

Open http://127.0.0.1:8000

### Search (experimental)

```powershell
agenttrace search "prompt text"
```

Search only works when a backend provides `search` (the SQLite backend, if wired).
