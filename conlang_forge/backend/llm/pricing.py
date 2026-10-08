"""Prices, in US dollars per million tokens. One dollar per million tokens is exactly one micro-dollar per token,
so cost in micro-dollars = tokens x price.

These defaults are APPROXIMATIONS to keep the cost graphs meaningful until real prices are entered: check them
against the provider's current price list and override them in the admin settings (`llm.prices`). A model with no
price is logged at cost 0 and flagged.
"""
from __future__ import annotations

DEFAULT_PRICES = {
    "claude-haiku-4-5-20251001": {"in": 1.0, "out": 5.0, "cache_write": 1.25, "cache_read": 0.10},
    "claude-sonnet-5-5": {"in": 3.0, "out": 15.0, "cache_write": 3.75, "cache_read": 0.30},
    "claude-opus-5-5": {"in": 5.0, "out": 25.0, "cache_write": 6.25, "cache_read": 0.50},
}


class Pricing:
    def __init__(self, overrides=None):
        self.table = {**DEFAULT_PRICES, **(overrides or {})}

    def known(self, model: str) -> bool:
        return model in self.table

    def cost_micro_usd(self, model: str, usage) -> int:
        p = self.table.get(model)
        if not p:
            return 0
        return round(usage.input_tokens * p["in"] + usage.output_tokens * p["out"]
                     + usage.cache_write_tokens * p.get("cache_write", p["in"])
                     + usage.cache_read_tokens * p.get("cache_read", p["in"]))
