"""Anthropic auto-instrumentation."""

import functools
import time
from typing import Any, Callable

from agenttrace.tracer import get_current_tracer

def instrument():
    try:
        import anthropic
    except ImportError:
        return

    # Patch anthropic.resources.messages.Messages.create
    try:
        from anthropic.resources.messages import Messages
        
        if not hasattr(Messages, "_original_create"):
            Messages._original_create = Messages.create
            Messages.create = _wrap_create(Messages._original_create)
            
    except ImportError:
        pass

def _wrap_create(original_create: Callable):
    @functools.wraps(original_create)
    def wrapper(self, *args, **kwargs):
        tracer = get_current_tracer()
        if not tracer:
            return original_create(self, *args, **kwargs)

        # Capture request
        model = kwargs.get("model")
        messages = kwargs.get("messages")
        
        span_id = tracer.new_span_id()
        tracer.llm_request(
            {"provider": "anthropic", "model": model, "messages": messages}, 
            span_id=span_id
        )

        start_ts = time.time()
        try:
            response = original_create(self, *args, **kwargs)
            duration_ms = (time.time() - start_ts) * 1000
            
            if not kwargs.get("stream"):
                # Anthropic response structure
                content = response.content[0].text if response.content else ""
                usage = {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                } if response.usage else {}
                
                tracer.llm_response(
                    {"content": content, "usage": usage, "duration_ms": duration_ms},
                    span_id=span_id
                )
            else:
                tracer.llm_response(
                    {"stream": True, "duration_ms": duration_ms},
                    span_id=span_id
                )
                
            return response
        except Exception as e:
            tracer.error(e, span_id=span_id)
            raise e
            
    return wrapper
