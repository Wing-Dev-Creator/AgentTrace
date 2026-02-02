# Pricing

AgentTrace includes a built-in cost estimation module that calculates the USD cost of LLM calls based on model name and token usage.

## How it works

When auto-instrumentation is enabled, each `llm_response` event includes a `cost_usd` field calculated from the model's pricing and the reported token counts.

The web UI displays this cost as a badge on each event card.

## Supported models

Prices are in USD per 1M tokens (input, output):

| Model | Input | Output |
|-------|------:|-------:|
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4-turbo | $10.00 | $30.00 |
| gpt-3.5-turbo | $0.50 | $1.50 |
| o1-preview | $15.00 | $60.00 |
| o1-mini | $3.00 | $12.00 |
| claude-3-5-sonnet | $3.00 | $15.00 |
| claude-3-opus | $15.00 | $75.00 |
| claude-3-haiku | $0.25 | $1.25 |

Model name matching is prefix-based, so versioned names like `gpt-4o-2024-05-13` are matched to `gpt-4o`.

## Programmatic usage

```python
from agenttrace.pricing import estimate_cost

cost = estimate_cost("gpt-4o", prompt_tokens=1000, completion_tokens=500)
# Returns 0.0075 (USD)
```

Returns `None` if the model is not in the pricing table.

## Adding models

Edit the `PRICING` dictionary in `agenttrace/pricing.py` to add new models or update prices.
