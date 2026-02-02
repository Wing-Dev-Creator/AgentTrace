"""OpenAI auto-instrumentation."""

import functools
import time
from typing import Any, Callable

from agenttrace.tracer import get_current_tracer

def instrument():
    try:
        import openai
    except ImportError:
        return

    # Wrap the sync client's create method
    # Note: Modern OpenAI SDK (v1+) uses `client.chat.completions.create`
    # We need to patch the Class method or the instance method?
    # Patching `openai.resources.chat.completions.Completions.create` is safer.
    
    try:
        from openai.resources.chat.completions import Completions
        
        if not hasattr(Completions, "_original_create"):
            Completions._original_create = Completions.create
            Completions.create = _wrap_create(Completions._original_create)
            
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
            {"model": model, "messages": messages}, 
            span_id=span_id
        )

        start_ts = time.time()
        try:
            response = original_create(self, *args, **kwargs)
            duration_ms = (time.time() - start_ts) * 1000
            
            # Extract response (simplistic for now, assumes non-streaming)
            # TODO: Handle stream=True
            if not kwargs.get("stream"):
                content = response.choices[0].message.content
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else {}
                
                tracer.llm_response(
                    {"content": content, "usage": usage, "duration_ms": duration_ms},
                    span_id=span_id
                )
            else:
                # For stream, we just log that we got a stream for now
                tracer.llm_response(
                    {"stream": True, "duration_ms": duration_ms},
                    span_id=span_id
                )
                
            return response
        except Exception as e:
            tracer.error(e, span_id=span_id)
            raise e
            
    return wrapper