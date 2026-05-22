from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from cache_rules.parser.transcripts import TranscriptTurn

# Anthropic bills cache reads at 0.10x and 5-minute cache writes at 1.25x the
# input rate. claude-rules treats every cache_creation token as a 5-minute
# write; the 1-hour TTL (2x) is not yet distinguished.
CACHE_READ_MULTIPLIER = 0.10
CACHE_WRITE_MULTIPLIER = 1.25

# TODO: replace the hardcoded rate with a live FX lookup.
DEFAULT_USD_TO_EUR = 0.92


@dataclass(frozen=True, slots=True)
class ModelPricing:
    """USD price per million tokens for a model."""

    input_per_mtok: float
    output_per_mtok: float


# Source: https://platform.claude.com/docs/en/about-claude/pricing (May 2026).
# TODO: fetch pricing dynamically instead of hardcoding.
PRICING: dict[str, ModelPricing] = {
    "claude-opus-4-7": ModelPricing(input_per_mtok=5.0, output_per_mtok=25.0),
    "claude-sonnet-4-6": ModelPricing(input_per_mtok=3.0, output_per_mtok=15.0),
    "claude-haiku-4-5": ModelPricing(input_per_mtok=1.0, output_per_mtok=5.0),
}


def pricing_for(model: str) -> ModelPricing | None:
    """Look up pricing, tolerating model ids that carry a date suffix."""
    for prefix, pricing in PRICING.items():
        if model.startswith(prefix):
            return pricing
    return None


def turn_cost_usd(turn: TranscriptTurn) -> float:
    """USD cost of a single turn. Unpriced models (e.g. <synthetic>) cost 0."""
    pricing = pricing_for(turn.model)
    if pricing is None:
        return 0.0
    input_rate = pricing.input_per_mtok / 1_000_000
    output_rate = pricing.output_per_mtok / 1_000_000
    return (
        turn.input_tokens * input_rate
        + turn.cache_creation_tokens * input_rate * CACHE_WRITE_MULTIPLIER
        + turn.cache_read_tokens * input_rate * CACHE_READ_MULTIPLIER
        + turn.output_tokens * output_rate
    )


def total_cost_usd(turns: Iterable[TranscriptTurn]) -> float:
    """USD cost of every turn combined."""
    return sum(turn_cost_usd(turn) for turn in turns)


def cost_without_cache_usd(turns: Iterable[TranscriptTurn]) -> float:
    """Hypothetical USD cost if every input token were billed at the plain input rate."""
    total = 0.0
    for turn in turns:
        pricing = pricing_for(turn.model)
        if pricing is None:
            continue
        input_rate = pricing.input_per_mtok / 1_000_000
        output_rate = pricing.output_per_mtok / 1_000_000
        uncached_input = (
            turn.input_tokens + turn.cache_creation_tokens + turn.cache_read_tokens
        )
        total += uncached_input * input_rate + turn.output_tokens * output_rate
    return total


def usd_to_eur(amount_usd: float, rate: float = DEFAULT_USD_TO_EUR) -> float:
    """Convert a USD amount to EUR."""
    return amount_usd * rate
