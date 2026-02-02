# Environment Variables

AgentTrace reads a few environment variables for storage and redaction.

## Storage

### `AGENTTRACE_ROOT`
Override the default trace directory.

Default:

```
~/.agenttrace/traces
```

Example:

```powershell
$env:AGENTTRACE_ROOT="D:\\agenttrace-data"
```

## Redaction

### `AGENTTRACE_STORE_FULL`
If set to `1`, disables truncation and stores full strings.

Default: `0`

### `AGENTTRACE_MAX_FIELD_LEN`
Max length for stored string fields (when `AGENTTRACE_STORE_FULL=0`).

Default: `512`

Example:

```powershell
$env:AGENTTRACE_MAX_FIELD_LEN="1024"
```

### `AGENTTRACE_REDACT`
Comma‑separated list of extra key names to redact.

Default keys already include:

```
authorization, api_key, password, token, access_token, secret
```

Example:

```powershell
$env:AGENTTRACE_REDACT="authorization,api_key,password,private_key"
```
