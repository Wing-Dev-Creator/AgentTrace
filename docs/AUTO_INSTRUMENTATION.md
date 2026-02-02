# Auto-Instrumentation

AgentTrace can automatically capture LLM calls from OpenAI, Anthropic, and LangChain without modifying your existing code.

## Setup

```python
from agenttrace import trace, instrument

# Enable all supported libraries
instrument()

# Or selectively
instrument(openai=True, anthropic=False, langchain=False)
```

Then wrap your agent logic in a trace context:

```python
with trace("my-run", project="my-project"):
    # All LLM calls inside this block are recorded automatically
    response = client.chat.completions.create(...)
```

## OpenAI

Wraps `chat.completions.create` for both sync and async clients, including streaming.

**Captured events:**
- `llm_request` — model, messages, stream flag
- `llm_response` — content, token usage, duration, estimated cost
- `error` — on exceptions

**Streaming:** The wrapper yields chunks transparently and emits an `llm_response` event with the accumulated content after the stream completes.

## Anthropic

Wraps `messages.create` for both sync and async clients.

**Captured events:**
- `llm_request` — model, messages
- `llm_response` — content, token usage, duration, estimated cost
- `error` — on exceptions

## LangChain

Uses a proxy callback handler that forwards events to the active tracer.

**Captured events:**
- `llm_request` / `llm_response` — LLM start/end
- `tool_call` / `tool_result` — tool start/end
- `retrieval` / `retrieval_end` — retriever start/end
- `error` — chain errors

The handler is registered automatically via `instrument(langchain=True)`. You can also use it directly:

```python
from agenttrace.langchain import AgentTraceCallbackHandler

handler = AgentTraceCallbackHandler()
chain.invoke({"input": "..."}, config={"callbacks": [handler]})
```

## Cost Tracking

All instrumented LLM calls include a `cost_usd` field in the response payload, estimated from the model name and token counts. See [PRICING.md](PRICING.md) for supported models.

## Requirements

The instrumented libraries must be installed separately:

```powershell
pip install openai        # for OpenAI instrumentation
pip install anthropic     # for Anthropic instrumentation
pip install langchain     # for LangChain instrumentation
```

If a library is not installed, its instrumentation is silently skipped.
