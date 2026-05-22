from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from cache_rules.metrics.cache import (
    cache_hit_rate,
    hit_rate_by_day,
    hit_rate_by_project,
    hit_rate_by_session,
)
from cache_rules.metrics.cost import (
    DEFAULT_USD_TO_EUR,
    cost_without_cache_usd,
    pricing_for,
    total_cost_usd,
    turn_cost_usd,
    usd_to_eur,
)
from cache_rules.parser.transcripts import TranscriptTurn


def _turn(
    *,
    session_id: str = "s1",
    project_path: str = "/p",
    model: str = "claude-opus-4-7",
    timestamp: datetime | None = None,
    input_tokens: int = 0,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
    output_tokens: int = 0,
    is_sidechain: bool = False,
) -> TranscriptTurn:
    return TranscriptTurn(
        timestamp=timestamp or datetime(2026, 5, 21, 12, 0, 0, tzinfo=UTC),
        session_id=session_id,
        project_path=project_path,
        model=model,
        input_tokens=input_tokens,
        cache_creation_tokens=cache_creation_tokens,
        cache_read_tokens=cache_read_tokens,
        output_tokens=output_tokens,
        is_sidechain=is_sidechain,
    )


def test_cache_hit_rate_is_cached_reads_over_total_input() -> None:
    turns = [
        _turn(input_tokens=100, cache_creation_tokens=300, cache_read_tokens=600),
        _turn(cache_read_tokens=1000),
    ]
    # cached reads 1600 / total input 2000
    assert cache_hit_rate(turns) == 0.8


def test_cache_hit_rate_is_zero_when_there_are_no_input_tokens() -> None:
    assert cache_hit_rate([]) == 0.0
    assert cache_hit_rate([_turn(output_tokens=500)]) == 0.0


def test_hit_rate_by_session_groups_by_session_id() -> None:
    turns = [
        _turn(session_id="a", cache_read_tokens=800, input_tokens=200),
        _turn(session_id="b", cache_read_tokens=500, cache_creation_tokens=500),
    ]
    assert hit_rate_by_session(turns) == {"a": 0.8, "b": 0.5}


def test_hit_rate_by_day_groups_by_calendar_date() -> None:
    turns = [
        _turn(
            timestamp=datetime(2026, 5, 20, 9, 0, 0, tzinfo=UTC),
            cache_read_tokens=900,
            input_tokens=100,
        ),
        _turn(
            timestamp=datetime(2026, 5, 21, 9, 0, 0, tzinfo=UTC),
            cache_read_tokens=250,
            cache_creation_tokens=750,
        ),
    ]
    assert hit_rate_by_day(turns) == {date(2026, 5, 20): 0.9, date(2026, 5, 21): 0.25}


def test_hit_rate_by_project_groups_by_project_path() -> None:
    turns = [
        _turn(project_path="/a", cache_read_tokens=600, input_tokens=400),
        _turn(project_path="/b", cache_read_tokens=100, input_tokens=900),
    ]
    assert hit_rate_by_project(turns) == {"/a": 0.6, "/b": 0.1}


def test_pricing_for_matches_model_ids_with_a_date_suffix() -> None:
    # real transcripts carry ids like "claude-haiku-4-5-20251001"
    assert pricing_for("claude-haiku-4-5-20251001") is pricing_for("claude-haiku-4-5")
    assert pricing_for("claude-opus-4-7") is not None
    assert pricing_for("<synthetic>") is None


def test_turn_cost_usd_applies_cache_multipliers() -> None:
    # opus 4.7: $5/MTok input, $25/MTok output
    turn = _turn(
        model="claude-opus-4-7",
        input_tokens=1_000_000,
        cache_creation_tokens=1_000_000,
        cache_read_tokens=1_000_000,
        output_tokens=1_000_000,
    )
    # 5.00 input + 6.25 cache write (1.25x) + 0.50 cache read (0.10x) + 25.00 output
    assert turn_cost_usd(turn) == pytest.approx(36.75)


def test_turn_cost_usd_is_zero_for_unpriced_models() -> None:
    assert turn_cost_usd(_turn(model="<synthetic>", input_tokens=999)) == 0.0


def test_total_cost_usd_sums_every_turn() -> None:
    turns = [
        _turn(
            model="claude-opus-4-7",
            input_tokens=1_000_000,
            cache_creation_tokens=1_000_000,
            cache_read_tokens=1_000_000,
            output_tokens=1_000_000,
        ),  # 36.75
        _turn(model="claude-opus-4-7", output_tokens=1_000_000),  # 25.00
    ]
    assert total_cost_usd(turns) == pytest.approx(61.75)


def test_cost_without_cache_usd_bills_every_input_token_at_the_plain_rate() -> None:
    turn = _turn(
        model="claude-opus-4-7",
        input_tokens=1_000_000,
        cache_creation_tokens=1_000_000,
        cache_read_tokens=1_000_000,
        output_tokens=1_000_000,
    )
    # 3M input tokens @ $5/MTok + 1M output @ $25/MTok
    assert cost_without_cache_usd([turn]) == pytest.approx(40.0)


def test_usd_to_eur_uses_the_default_rate_or_an_override() -> None:
    assert usd_to_eur(100.0) == pytest.approx(100.0 * DEFAULT_USD_TO_EUR)
    assert usd_to_eur(100.0, rate=0.5) == pytest.approx(50.0)
