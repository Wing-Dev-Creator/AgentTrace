# AgentTrace 🕵️‍♂️

**High-performance AI telemetry & replay system.**
Think "Datadog for AI Agents" — but local-first, fast, and replayable.

AgentTrace records every step of your AI agent's execution (prompts, tool calls, responses, errors) and lets you **visualize**, **replay**, and **debug** them effortlessly.

## 🚀 Why AgentTrace?

Debugging AI agents is painful. Text logs are messy. SaaS tools are slow/expensive.
**AgentTrace** solves this by providing:

*   **🔍 Full Observability:** Capture inputs, LLM requests/responses, tool usage, and errors in structured JSONL (CRC optional).
*   **📺 Visual Timeline:** A beautiful local web UI to inspect traces (no cloud required).
*   **🔁 Deterministic Replay:** (Coming Soon) Re-run traces with mocked inputs to verify fixes without burning tokens.
*   **🏎️ High Performance:** Minimal overhead, designed for production telemetry.

## 📦 Installation

```powershell
# Install directly
pip install agenttrace

# OR for development
git clone https://github.com/yourusername/agenttrace.git
cd agenttrace
pip install -e .
```

## ⚡ Quick Start

### 1. Instrument your code
Wrap your agent logic with `Tracer`. It works with any Python code (LangChain, LlamaIndex, or raw API calls).

```python
from agenttrace import Tracer

# Start a trace
with Tracer(trace_name="demo_run", project="my-agent") as t:
    # 1. Log user input
    t.user_input("What's the weather in Tokyo?")
    
    # 2. Log LLM interaction
    t.llm_request({
        "model": "gpt-4o", 
        "messages": [{"role": "user", "content": "What's the weather in Tokyo?"}]
    })
    
    # ... your agent logic ...
    
    t.llm_response({"content": "It is currently sunny..."})
```

### 2. Visualize traces
Launch the local UI to see your traces in a timeline view.

```powershell
pip install -e .[ui]
agenttrace ui
```
Then open **http://127.0.0.1:8000** in your browser.

### 3. Inspect via CLI
Quickly dump trace data in your terminal.

```powershell
agenttrace ls
agenttrace inspect <trace_id>
agenttrace replay <trace_id>
agenttrace replay <trace_id> --step
agenttrace replay <trace_id> --kind llm_request --kind tool_call
agenttrace replay <trace_id> --span s1
agenttrace diff <trace_a> <trace_b>
agenttrace export <trace_id> --out trace.json
```

## Docs

- `docs/FORMAT.md` — JSONL event format and CRC suffix
- `docs/BACKENDS.md` — native vs fallback storage behavior
- `docs/CLI.md` — CLI commands and flags
- `docs/ENV.md` — environment variables
- `docs/TESTING.md` — how to run tests and native builds
- `docs/STATUS.md` — current repo state and next steps

## 🗺️ Roadmap & Progress

We are building a comprehensive observability platform.

| Feature | Status | Description |
| :--- | :---: | :--- |
| **Telemetry Recording** | ✅ Beta | Structured logging (JSONL) for LLMs & Tools. |
| **Local Web UI** | ✅ Beta | Timeline visualization of agent execution. |
| **Deterministic Replay** | ⏳ Planned | Re-run agents using recorded artifacts. |
| **LangChain Integration** | 🚧 WIP | Auto-instrumentation for LangChain agents. |
| **Binary Storage** | ⏳ Planned | High-speed, compact storage (SQLite/Parquet). |
| **Diff & Search** | 🚧 WIP | Compare runs side-by-side; full-text search. |

## 🤝 Contributing

We are in early development! PRs are welcome.

See [ARCHITECTURE.md](ARCHITECTURE.md) for a system overview.

### Development Setup

1.  Clone the repo.
2.  **Python:** Install dependencies: `pip install -e .` (requires Rust toolchain)
3.  **Rust:** (Optional) If working on core: `cargo test`
4.  **Native Extension:** `maturin develop --release` to build `agenttrace_native`
5.  Run the example: `python examples/langchain_basic.py`
6.  Start the UI: `agenttrace ui`
