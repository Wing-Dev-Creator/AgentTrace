# Web UI

AgentTrace includes a local web UI for visualizing traces as interactive timelines.

## Starting the server

```powershell
pip install agenttrace[ui]
agenttrace ui
agenttrace ui --port 9000 --host 0.0.0.0
```

Opens at **http://127.0.0.1:8000** by default.

## Features

- **Trace list** — sidebar showing all recorded traces, sorted by time
- **Timeline view** — color-coded event cards with kind icons, timestamps, and payload details
- **Search** — filter traces by searching event payloads and attributes
- **Cost display** — shows `cost_usd` from instrumented LLM calls
- **RAG preview** — retrieval events show document snippet cards

## REST API

The server exposes a JSON API that the UI consumes:

### `GET /api/traces`

Returns a list of all traces.

```json
[
  {
    "id": "abc-123",
    "name": "my-agent-run",
    "project": "my-project",
    "ts": 1706889600.0,
    "event_count": 12
  }
]
```

### `GET /api/traces/{trace_id}`

Returns full trace details with all events.

```json
{
  "id": "abc-123",
  "trace_name": "my-agent-run",
  "project": "my-project",
  "events": [
    {
      "schema_version": 1,
      "trace_id": "abc-123",
      "seq": 0,
      "ts_unix_ns": 1706889600000000000,
      "kind": "trace_start",
      "span_id": null,
      "parent_span_id": null,
      "level": "info",
      "attrs": {},
      "payload": {"trace_name": "my-agent-run", "project": "my-project"}
    }
  ]
}
```

### `GET /api/search?q={query}`

Searches event payloads and attributes across all traces. Returns matching events.

## Requirements

The UI requires FastAPI and uvicorn:

```powershell
pip install agenttrace[ui]
```
