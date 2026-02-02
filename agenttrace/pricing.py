"""Model pricing registry."""

from typing import Dict, Optional

# Prices in USD per 1M tokens (as of Feb 2026 approximation)
# (Input, Output)
PRICING: Dict[str, tuple[float, float]] = {
    # OpenAI
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    "o1-preview": (15.00, 60.00),
    "o1-mini": (3.00, 12.00),
    
    # Anthropic
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-opus": (15.00, 75.00),
    "claude-3-haiku": (0.25, 1.25),
}

def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> Optional[float]:
    """Calculate estimated cost in USD."""
    if not model:
        return None
    
    # Normalize model name (handle dates/versions like gpt-4o-2024-05-13)
    base_model = model
    for key in PRICING:
        if model.startswith(key):
            base_model = key
            break
            
    if base_model not in PRICING:
        return None
        
    input_price, output_price = PRICING[base_model]
    
    cost = (prompt_tokens * input_price / 1_000_000) + (completion_tokens * output_price / 1_000_000)
    return round(cost, 6)
