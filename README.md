# AgentTrace

**High-performance AI telemetry & replay system.**
Think "Datadog for AI Agents" — but local-first, fast, and replayable.

AgentTrace records every step of your AI agent's execution (prompts, tool calls, responses, errors) and lets you **visualize**, **replay**, and **debug** them.

## Why AgentTrace?

Debugging AI agents is painful. Text logs are messy. SaaS tools are slow/expensive.
**AgentTrace** solves this by providing:

- **Full Observability:** Capture inputs, LLM requests/responses, tool usage, and errors in structured JSONL with CRC integrity.
- **Auto-Instrumentation:** One-line setup for OpenAI, Anthropic, and LangChain.
- **Visual Timeline:** A local web UI to inspect traces (no cloud required).
- **Cost Tracking:** Automatic LLM cost estimation per call.
- **Deterministic Replay:** Re-run traces with mocked inputs to verify fixes without burning tokens.
- **High Performance:** Rust-powered I/O with pure-Python fallback.

## Installation

```powershell
# Install directly
pip install agenttrace

# With web UI support
pip install agenttrace[ui]

# For development (requires Rust toolchain)
git clone https://github.com/Wing-Dev-Creator/AgentTrace.git
cd AgentTrace
maturin develop --release
pip install -e .[ui]
```

## Quick Start

### 1. Auto-Instrumentation (recommended)

```python
from agenttrace import trace, instrument

# Enable auto-instrumentation for OpenAI, Anthropic, LangChain
instrument()

with trace("my-agent-run", project="my-project"):
    # Your existing code works unchanged — all LLM calls are captured automatically
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello!"}]
    )
```

### 2. Manual Instrumentation

```python
from agenttrace import Tracer

with Tracer(trace_name="demo_run", project="my-agent") as t:
    t.user_input("What's the weather in Tokyo?")

    t.llm_request({
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "What's the weather in Tokyo?"}]
    })

    # ... your agent logic ...

    t.llm_response({"content": "It is currently sunny..."})
```

### 3. Visualize traces

```powershell
pip install agenttrace[ui]
agenttrace ui
```

Then open **http://127.0.0.1:8000** in your browser.

### 4. Inspect via CLI

```powershell
agenttrace ls
agenttrace inspect <trace_id>
agenttrace search "some query"
agenttrace replay <trace_id>
agenttrace replay <trace_id> --step
agenttrace diff <trace_a> <trace_b>
agenttrace export <trace_id> --out trace.json
```

## Docs

- [docs/FORMAT.md](docs/FORMAT.md) — JSONL event format and CRC suffix
- [docs/BACKENDS.md](docs/BACKENDS.md) — native vs fallback storage behavior
- [docs/CLI.md](docs/CLI.md) — CLI commands and flags
- [docs/ENV.md](docs/ENV.md) — environment variables
- [docs/TESTING.md](docs/TESTING.md) — how to run tests and native builds
- [docs/STATUS.md](docs/STATUS.md) — current repo state and next steps
- [docs/AUTO_INSTRUMENTATION.md](docs/AUTO_INSTRUMENTATION.md) — OpenAI, Anthropic, LangChain setup
- [docs/REDACTION.md](docs/REDACTION.md) — privacy and secret scrubbing
- [docs/REPLAY.md](docs/REPLAY.md) — deterministic replay API
- [docs/PRICING.md](docs/PRICING.md) — LLM cost estimation
- [docs/UI.md](docs/UI.md) — web UI and REST API

## Roadmap

| Feature | Status | Description |
| :--- | :---: | :--- |
| **Telemetry Recording** | Done | Structured JSONL logging for LLMs & tools |
| **Local Web UI** | Done | Timeline visualization of agent execution |
| **Auto-Instrumentation** | Done | OpenAI, Anthropic, LangChain support |
| **Cost Tracking** | Done | Per-call LLM cost estimation |
| **Redaction** | Done | Automatic API key and secret scrubbing |
| **Diff & Search** | Done | Compare runs side-by-side; text search |
| **Deterministic Replay** | Beta | Re-run agents using recorded artifacts |

## Contributing

PRs are welcome. See [ARCHITECTURE.md](ARCHITECTURE.md) for a system overview.

### Development Setup

1. Clone the repo
2. Install Rust toolchain and maturin: `pip install maturin`
3. Build native extension: `maturin develop --release`
4. Install Python package: `pip install -e .[ui]`
5. Run tests: `cargo test && python -m pytest tests/`
6. Start the UI: `agenttrace ui`
