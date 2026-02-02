"""LangChain auto-instrumentation."""

from __future__ import annotations

from typing import Any, Optional

from agenttrace.tracer import get_current_tracer, Tracer
from agenttrace.langchain import AgentTraceCallbackHandler

# We need a proxy handler that delegates to the CURRENT tracer context.
# Standard LangChain handlers are instantiated once, but our Tracer is ephemeral (per context).

class ProxyCallbackHandler(AgentTraceCallbackHandler):
    def __init__(self) -> None:
        # Initialize internal state only — no super().__init__() since
        # we dynamically resolve the tracer via property.
        self._run_to_span: dict[str, str] = {}

    @property
    def tracer(self) -> Tracer:
        t = get_current_tracer()
        if not t:
            return _DummyTracer()
        return t

    @tracer.setter
    def tracer(self, value: Any) -> None:
        pass  # Ignore writes


class _DummyTracer:
    """No-op tracer used when no active trace context exists."""

    def emit(self, *args: Any, **kwargs: Any) -> None:
        pass

    def new_span_id(self) -> str:
        return "noop"

    def llm_request(self, *args: Any, **kwargs: Any) -> None:
        pass

    def llm_response(self, *args: Any, **kwargs: Any) -> None:
        pass

    def tool_call(self, *args: Any, **kwargs: Any) -> None:
        pass

    def tool_result(self, *args: Any, **kwargs: Any) -> None:
        pass

    def error(self, *args: Any, **kwargs: Any) -> None:
        pass

    def __enter__(self) -> _DummyTracer:
        return self

    def __exit__(self, *args: Any) -> None:
        pass


def instrument() -> None:
    try:
        import langchain  # noqa: F401
    except ImportError:
        return

    # LangChain has a global configuration hook system for tracers.
    # But usually people just want "add this handler to everything".
    # We can try setting `langchain.callbacks.global_handler` if it existed, 
    # but the modern way is via `langchain_core.callbacks.manager`.
    
    # We will try to monkeypatch the default callback manager construction
    # OR simpler: check if we can add a global handler.
    
    # LangChain doesn't really have a "Global Callback Handler" list exposed easily 
    # that applies to ALL chains automatically unless configured via env vars or context.
    
    # Strategy: Patch `CallbackManager.configure` which is called by nearly all chains
    # to resolve their callbacks.
    
    try:
        from langchain_core.callbacks import CallbackManager
        
        if not hasattr(CallbackManager, "_original_configure"):
            CallbackManager._original_configure = CallbackManager.configure
            
            @classmethod
            def _configure(cls, *args, **kwargs):
                # Get standard result
                handlers = cls._original_configure(*args, **kwargs)
                
                # Add our proxy handler if not present
                # Note: handlers is a CallbackManager instance
                
                # Check if we are inside an AgentTrace context
                if get_current_tracer():
                    # Check if already added to avoid dupes (naive check)
                    if not any(isinstance(h, ProxyCallbackHandler) for h in handlers.handlers):
                        handlers.add_handler(ProxyCallbackHandler())
                        
                return handlers

            CallbackManager.configure = _configure
            
    except ImportError:
        pass
