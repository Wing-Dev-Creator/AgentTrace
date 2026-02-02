"""LangChain callback handler (minimal scaffold)."""

from __future__ import annotations

__all__ = ["AgentTraceCallbackHandler"]

from typing import Any, Dict, Optional

from .tracer import Tracer

try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:
    try:
        from langchain.callbacks.base import BaseCallbackHandler
    except (ImportError, ModuleNotFoundError):  # optional dependency
        BaseCallbackHandler = object  # type: ignore[assignment]


class AgentTraceCallbackHandler(BaseCallbackHandler):
    def __init__(self, tracer: Tracer):
        self.tracer = tracer
        self._run_to_span: Dict[str, str] = {}

    def _span_for_run(self, run_id: str) -> Optional[str]:
        return self._run_to_span.get(run_id)

    def _create_span(self, run_id: str) -> str:
        span_id = self.tracer.new_span_id()
        self._run_to_span[run_id] = span_id
        return span_id

    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], run_id: str, parent_run_id: Optional[str] = None, **kwargs: Any) -> None:
        span_id = self._create_span(run_id)
        parent_span_id = self._span_for_run(parent_run_id) if parent_run_id else None
        self.tracer.emit(
            "span_start",
            payload={"name": (serialized or {}).get("name") or "chain", "inputs": inputs},
            attrs={"type": "chain"},
            span_id=span_id,
            parent_span_id=parent_span_id,
        )

    def on_chain_end(self, outputs: Dict[str, Any], run_id: str, **kwargs: Any) -> None:
        span_id = self._span_for_run(run_id)
        self.tracer.emit(
            "span_end",
            payload={"outputs": outputs},
            attrs={"type": "chain"},
            span_id=span_id,
        )
        self._run_to_span.pop(run_id, None)

    def on_llm_start(self, serialized: Dict[str, Any], prompts: Any, run_id: str, parent_run_id: Optional[str] = None, **kwargs: Any) -> None:
        span_id = self._create_span(run_id)
        parent_span_id = self._span_for_run(parent_run_id) if parent_run_id else None
        attrs = {
            "provider": ((serialized or {}).get("id") or ["llm"])[-1],
            "model": (kwargs.get("invocation_params") or {}).get("model_name"),
        }
        self.tracer.emit(
            "llm_request",
            payload={"prompts": prompts},
            attrs=attrs,
            span_id=span_id,
            parent_span_id=parent_span_id,
        )

    def on_llm_end(self, response: Any, run_id: str, **kwargs: Any) -> None:
        span_id = self._span_for_run(run_id)
        self.tracer.emit(
            "llm_response",
            payload={"response": getattr(response, "generations", None)},
            span_id=span_id,
        )
        self._run_to_span.pop(run_id, None)

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, run_id: str, parent_run_id: Optional[str] = None, **kwargs: Any) -> None:
        span_id = self._create_span(run_id)
        parent_span_id = self._span_for_run(parent_run_id) if parent_run_id else None
        self.tracer.emit(
            "tool_call",
            payload={"input": input_str},
            attrs={"tool": (serialized or {}).get("name")},
            span_id=span_id,
            parent_span_id=parent_span_id,
        )

    def on_tool_end(self, output: Any, run_id: str, **kwargs: Any) -> None:
        span_id = self._span_for_run(run_id)
        self.tracer.emit("tool_result", payload={"output": output}, span_id=span_id)
        self._run_to_span.pop(run_id, None)

    def on_retriever_start(self, serialized: Dict[str, Any], query: str, run_id: str, parent_run_id: Optional[str] = None, **kwargs: Any) -> None:
        span_id = self._create_span(run_id)
        parent_span_id = self._span_for_run(parent_run_id) if parent_run_id else None
        self.tracer.emit(
            "retrieval_start", # We split start/end to track latency
            payload={"query": query},
            attrs={"retriever": (serialized or {}).get("name") or "retriever"},
            span_id=span_id,
            parent_span_id=parent_span_id,
        )

    def on_retriever_end(self, documents: Any, run_id: str, **kwargs: Any) -> None:
        span_id = self._span_for_run(run_id)
        # documents is Sequence[Document]
        # specific to LangChain
        docs_data = []
        try:
            for d in documents:
                doc = {"content": getattr(d, "page_content", str(d))}
                if hasattr(d, "metadata") and d.metadata:
                    doc["metadata"] = d.metadata
                docs_data.append(doc)
        except Exception:
            docs_data = [{"error": "failed to serialize documents"}]

        self.tracer.emit(
            "retrieval_end",
            payload={"documents": docs_data},
            span_id=span_id
        )
        self._run_to_span.pop(run_id, None)

    def on_error(self, error: Exception, run_id: str, **kwargs: Any) -> None:
        span_id = self._span_for_run(run_id)
        self.tracer.emit("error", payload={"error": repr(error)}, level="error", span_id=span_id)
        self._run_to_span.pop(run_id, None)
