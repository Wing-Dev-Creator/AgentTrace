"""Top-level instrumentation entry point."""

from .openai import instrument as instrument_openai
from .anthropic import instrument as instrument_anthropic
from .langchain import instrument as instrument_langchain

def instrument(openai=True, anthropic=True, langchain=True):
    """Enable auto-instrumentation for supported libraries."""
    if openai:
        instrument_openai()
    if anthropic:
        instrument_anthropic()
    if langchain:
        instrument_langchain()
