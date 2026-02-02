"""OpenAI auto-instrumentation."""

import functools
import time
from typing import Any, Callable

from agenttrace.tracer import get_current_tracer
from agenttrace.pricing import estimate_cost

def instrument():
    try:
        import openai
    except ImportError:
        return

    try:
        from openai.resources.chat.completions import Completions, AsyncCompletions
        
        if not hasattr(Completions, "_original_create"):
            Completions._original_create = Completions.create
            Completions.create = _wrap_create(Completions._original_create)

        if not hasattr(AsyncCompletions, "_original_create"):
            AsyncCompletions._original_create = AsyncCompletions.create
            AsyncCompletions.create = _wrap_async_create(AsyncCompletions._original_create)
            
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
        is_streaming = kwargs.get("stream", False)
        
        span_id = tracer.new_span_id()
        tracer.llm_request(
            {"model": model, "messages": messages, "stream": is_streaming}, 
            span_id=span_id
        )

        start_ts = time.time()
        try:
            response = original_create(self, *args, **kwargs)

            if not is_streaming:
                duration_ms = (time.time() - start_ts) * 1000
                content = response.choices[0].message.content
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else {}

                cost = estimate_cost(
                    model,
                    usage.get("prompt_tokens", 0),
                    usage.get("completion_tokens", 0)
                )

                tracer.llm_response(
                    {
                        "content": content,
                        "usage": usage,
                        "duration_ms": duration_ms,
                        "cost_usd": cost
                    },
                    span_id=span_id
                )
                return response
            else:
                return _wrap_stream_response(response, tracer, span_id, start_ts)

        except Exception as e:
            tracer.error(e, span_id=span_id)
            raise
            
    return wrapper

def _wrap_async_create(original_create: Callable):
    @functools.wraps(original_create)
    async def wrapper(self, *args, **kwargs):
        tracer = get_current_tracer()
        if not tracer:
            return await original_create(self, *args, **kwargs)

        # Capture request
        model = kwargs.get("model")
        messages = kwargs.get("messages")
        is_streaming = kwargs.get("stream", False)
        
        span_id = tracer.new_span_id()
        tracer.llm_request(
            {"model": model, "messages": messages, "stream": is_streaming}, 
            span_id=span_id
        )

        start_ts = time.time()
        try:
            response = await original_create(self, *args, **kwargs)
            
            if not is_streaming:
                duration_ms = (time.time() - start_ts) * 1000
                content = response.choices[0].message.content
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else {}
                
                cost = estimate_cost(
                    model, 
                    usage.get("prompt_tokens", 0), 
                    usage.get("completion_tokens", 0)
                )
                
                tracer.llm_response(
                    {
                        "content": content, 
                        "usage": usage, 
                        "duration_ms": duration_ms,
                        "cost_usd": cost
                    },
                    span_id=span_id
                )
                return response
            else:
                return _wrap_async_stream_response(response, tracer, span_id, start_ts)
                
        except Exception as e:
            tracer.error(e, span_id=span_id)
            raise

    return wrapper

def _wrap_stream_response(stream, tracer, span_id, start_ts):
    full_content = []
    
    for chunk in stream:
        if chunk.choices and len(chunk.choices) > 0:
            delta = chunk.choices[0].delta
            if hasattr(delta, "content") and delta.content:
                full_content.append(delta.content)
        yield chunk
    
    duration_ms = (time.time() - start_ts) * 1000
    accumulated_text = "".join(full_content)
    
    tracer.llm_response(
        {
            "content": accumulated_text, 
            "stream": True, 
            "duration_ms": duration_ms,
            "finish_reason": "completed"
        },
        span_id=span_id
    )

async def _wrap_async_stream_response(stream, tracer, span_id, start_ts):
    full_content = []
    
    async for chunk in stream:
        if chunk.choices and len(chunk.choices) > 0:
            delta = chunk.choices[0].delta
            if hasattr(delta, "content") and delta.content:
                full_content.append(delta.content)
        yield chunk
    
    duration_ms = (time.time() - start_ts) * 1000
    accumulated_text = "".join(full_content)
    
    tracer.llm_response(
        {
            "content": accumulated_text, 
            "stream": True, 
            "duration_ms": duration_ms,
            "finish_reason": "completed"
        },
        span_id=span_id
    )