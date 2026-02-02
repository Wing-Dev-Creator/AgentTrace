# AgentTrace Status (2026-02-02)

This document is a snapshot of the repository as it exists today and a
prioritized list of next improvements.

## What works today

- **Recording:** Tracer writes structured JSONL events with redaction.
- **Backends:** Rust native writer/reader (PyO3) with Python fallback.
- **CLI:** `ls`, `inspect`, `replay` (timeline view), `diff`, `export`, `ui`.
- **UI:** Local FastAPI server + static HTML timeline viewer.
- **Examples:** LangChain/LangGraph demos and replay/diff examples.
- **Tests:** Python tests cover tracer, reader, redaction, CLI, replayer.

## Current gaps / risks

- **Deterministic replay:** `agenttrace.replayer` is still a minimal stub
  (LLM request/response only). No tool/error replay or divergence checks.
- **UI interactivity:** No span tree, zoomable timeline, filters, or diff view.
- **Search/indexing:** Search is substring over JSON; no real index for scale.
- **Schema drift:** Event `kind` values are not fully standardized
  (`retrieval_start`/`retrieval_end` exist in code; docs list `retrieval`).
- **Token/cost summary:** No reliable aggregation or display yet.

## Recommended next steps (highest impact first)

1. **Deterministic replay engine**
   - Add `expect_tool_call`, `expect_tool_result`, `expect_error`.
   - Add divergence detection (by kind + span + key fields).
   - Add "what‑if" overrides for specific payload fields.

2. **UI overhaul**
   - Span hierarchy tree + collapsible nodes.
   - Timeline zoom/scroll (time‑scaled layout).
   - Filters: kind, model, tool, error only.
   - Side‑by‑side diff for two traces.

3. **Search & indexing**
   - Add SQLite read index (events + FTS).
   - Keep JSONL as write‑ahead log; build index on demand.

4. **Instrumentation coverage**
   - Harden LangChain callbacks for streaming, tools, retrievers.
   - Add OpenAI/Anthropic wrappers (request/response capture).

5. **Export / integration**
   - Export to OpenTelemetry (trace/span mapping).
   - Export to CSV/Parquet for analysis.

## Definition of "MVP done"

AgentTrace is MVP‑complete when a LangGraph user can:

- Add a callback handler
- Run their agent
- Replay the trace in CLI and UI
- Understand why a run diverged from a prior run
