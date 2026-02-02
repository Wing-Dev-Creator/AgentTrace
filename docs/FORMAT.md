# AgentTrace Event Format (JSONL + CRC)

AgentTrace stores each trace as a JSONL file:

```
~/.agenttrace/traces/<trace_id>/events.jsonl
```

Each line is a JSON object representing a single event.  
The native Rust writer appends an optional CRC32C suffix:

```
<json>\t<8-hex-crc32c>
```

The fallback Python reader accepts both plain JSONL and CRC‑suffixed lines.

## Event schema (MVP)

Required fields:

- `schema_version` (int, current: 1)
- `trace_id` (string, UUID hex)
- `seq` (int, monotonic per trace)
- `ts_unix_ns` (int, unix nanoseconds)
- `kind` (string enum)
- `level` (string: info|warn|error)
- `attrs` (object)
- `payload` (object)

Optional fields:

- `span_id` (string)
- `parent_span_id` (string)

### Core `kind` values

- `trace_start`, `trace_end`
- `user_input`
- `llm_request`, `llm_response`
- `tool_call`, `tool_result`
- `error`
- `span_start`, `span_end`
- `retrieval_start`, `retrieval_end` (LangChain retrievers)

### Payload conventions (non‑schema, but expected)

- `trace_start.payload`: `{ "trace_name": str, "project": str | null }`
- `span_start.payload`: `{ "name": str, "inputs": object }`
- `span_end.payload`: `{ "outputs": object }` plus optional `duration_ms`
- `span_end.payload.auto_closed`: `true` when the tracer closes spans on exit
- `llm_request.payload`: prompt/messages and optional model metadata
- `llm_response.payload`: response content/generations
- `tool_call.payload`: tool arguments/input
- `tool_result.payload`: tool output/result
- `retrieval_start.payload`: `{ "query": str }`
- `retrieval_end.payload`: `{ "documents": [...] }`

## Example line (no CRC)

```json
{"schema_version":1,"trace_id":"abc...","seq":1,"ts_unix_ns":1700000000000000000,"kind":"trace_start","span_id":null,"parent_span_id":null,"level":"info","attrs":{},"payload":{"trace_name":"demo","project":"my-agent"}}
```

## Example line (CRC suffix)

```text
{"schema_version":1,"trace_id":"abc...","seq":1,"ts_unix_ns":1700000000000000000,"kind":"trace_start","span_id":null,"parent_span_id":null,"level":"info","attrs":{},"payload":{"trace_name":"demo","project":"my-agent"}}	1a2b3c4d
```

## Compatibility

- CRC suffix is optional and ignored by the pure‑Python reader.
- Unknown fields are preserved when reading and replaying events.
