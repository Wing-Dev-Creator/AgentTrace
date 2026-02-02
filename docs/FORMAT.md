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

## Example line (no CRC)

```json
{"trace_id":"abc...","seq":1,"ts_unix_ns":1700000000000000000,"kind":"trace_start","span_id":null,"parent_span_id":null,"level":"info","attrs":{},"payload":{"trace_name":"demo","project":"my-agent"}}
```

## Example line (CRC suffix)

```text
{"trace_id":"abc...","seq":1,"ts_unix_ns":1700000000000000000,"kind":"trace_start","span_id":null,"parent_span_id":null,"level":"info","attrs":{},"payload":{"trace_name":"demo","project":"my-agent"}}	1a2b3c4d
```

## Compatibility

- CRC suffix is optional and ignored by the pure‑Python reader.
- Unknown fields are preserved when reading and replaying events.
