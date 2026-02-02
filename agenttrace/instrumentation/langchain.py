"""LangChain auto-instrumentation."""

from typing import Optional

from agenttrace.tracer import get_current_tracer, Tracer
from agenttrace.langchain import AgentTraceCallbackHandler

# We need a proxy handler that delegates to the CURRENT tracer context.
# Standard LangChain handlers are instantiated once, but our Tracer is ephemeral (per context).

class ProxyCallbackHandler(AgentTraceCallbackHandler):
    def __init__(self):
        # Initialize internal state
        self._run_to_span = {}
        # We don't pass a specific tracer here, the property handles it

    @property
    def tracer(self) -> Tracer:
        # Dynamically resolve the current tracer
        t = get_current_tracer()
        if not t:
            # Fallback to a dummy tracer or raise? 
            # Ideally return a dummy that does nothing to avoid crashing user code
            # if they run outside a 'with trace:' block.
            return _DummyTracer() 
        return t
    
    @tracer.setter
    def tracer(self, value):
        pass # Ignore writes

class _DummyTracer(Tracer):
    def emit(self, *args, **kwargs): pass
    def __enter__(self): return self
    def __exit__(self, *args): pass


def instrument():
    try:
        import langchain
        from langchain_core.tracers.context import register_configure_hook
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
