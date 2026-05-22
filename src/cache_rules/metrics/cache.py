from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import date
from typing import TypeVar

from cache_rules.parser.transcripts import TranscriptTurn

_K = TypeVar("_K")


def cache_hit_rate(turns: Iterable[TranscriptTurn]) -> float:
    """Fraction of input tokens served from cache: read / (read + creation + uncached)."""
    cached = 0
    total = 0
    for turn in turns:
        cached += turn.cache_read_tokens
        total += turn.cache_read_tokens + turn.cache_creation_tokens + turn.input_tokens
    return cached / total if total else 0.0


def hit_rate_by_session(turns: Iterable[TranscriptTurn]) -> dict[str, float]:
    """Cache hit rate computed independently for each session."""
    return _hit_rate_grouped(turns, lambda turn: turn.session_id)


def hit_rate_by_day(turns: Iterable[TranscriptTurn]) -> dict[date, float]:
    """Cache hit rate computed independently for each calendar day."""
    return _hit_rate_grouped(turns, lambda turn: turn.timestamp.date())


def hit_rate_by_project(turns: Iterable[TranscriptTurn]) -> dict[str, float]:
    """Cache hit rate computed independently for each project path."""
    return _hit_rate_grouped(turns, lambda turn: turn.project_path)


def _hit_rate_grouped(
    turns: Iterable[TranscriptTurn], key: Callable[[TranscriptTurn], _K]
) -> dict[_K, float]:
    groups: dict[_K, list[TranscriptTurn]] = defaultdict(list)
    for turn in turns:
        groups[key(turn)].append(turn)
    return {group_key: cache_hit_rate(group) for group_key, group in groups.items()}
