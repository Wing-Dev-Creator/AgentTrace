# Redaction

AgentTrace automatically scrubs sensitive data before writing events to disk.

## How it works

The `Redactor` class processes all event payloads and attributes before they are serialized. It applies two types of redaction:

1. **Key-based** — dictionary keys matching known secret names are replaced with `<redacted>`.
2. **Pattern-based** — string values are scanned with regex patterns for API keys, tokens, and credentials.

## Default redacted keys

Any dictionary key matching these names (case-insensitive) is redacted:

- `authorization`, `api_key`, `apikey`, `password`, `token`
- `access_token`, `secret`, `openai_api_key`, `anthropic_api_key`, `bearer`

## Default patterns

String values are scanned for:

- `sk-` prefixed keys (OpenAI-style)
- `Bearer` tokens
- `authorization: ...` headers
- `api_key=...` or `api-key=...` assignments
- `password=...` assignments

## Truncation

By default, string fields longer than 512 characters are truncated with a `...(truncated)` suffix. This keeps trace files manageable without losing important context.

## Configuration

Control redaction via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTTRACE_STORE_FULL` | `false` | Set to `true` to disable truncation and store full payloads |
| `AGENTTRACE_MAX_FIELD_LEN` | `512` | Maximum string length before truncation |
| `AGENTTRACE_REDACT` | *(empty)* | Comma-separated extra key names to redact |

See [ENV.md](ENV.md) for all environment variables.

## Depth limiting

Nested structures deeper than 6 levels are replaced with `<depth_limit>` to prevent excessive recursion.

## Bytes handling

- With `AGENTTRACE_STORE_FULL=true`: bytes are base64-encoded.
- Otherwise: replaced with `<bytes:len=N>`.

## Pydantic / dataclass support

Objects with `model_dump()` (Pydantic) or `__dict__` are automatically converted to dicts before redaction.
