from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from rich.console import Console
from rich.table import Table

from cache_rules.metrics.cache import cache_hit_rate
from cache_rules.metrics.cost import cost_without_cache_usd, total_cost_usd
from cache_rules.parser.transcripts import TranscriptTurn

HIT_RATE_TARGET = 0.90


@dataclass(frozen=True, slots=True)
class SessionBreakdown:
    """Per-session cache figures, used to surface the worst offenders."""

    session_id: str
    project_path: str
    hit_rate: float
    cost_usd: float


@dataclass(frozen=True, slots=True)
class CacheReport:
    """Summary of cache behaviour over a window of transcript turns."""

    window_days: int
    project_filter: str | None
    turn_count: int
    hit_rate: float
    cache_read_tokens: int
    cache_creation_tokens: int
    uncached_input_tokens: int
    output_tokens: int
    cost_usd: float
    cost_without_cache_usd: float
    worst_sessions: list[SessionBreakdown]


def build_cache_report(
    turns: Iterable[TranscriptTurn],
    *,
    window_days: int,
    project_filter: str | None,
    now: datetime,
    worst_n: int = 3,
) -> CacheReport:
    """Compute a CacheReport from transcript turns inside the window and project filter."""
    since = now - timedelta(days=window_days)
    turns = [
        turn
        for turn in turns
        if turn.timestamp >= since
        and (project_filter is None or project_filter in turn.project_path)
    ]
    return CacheReport(
        window_days=window_days,
        project_filter=project_filter,
        turn_count=len(turns),
        hit_rate=cache_hit_rate(turns),
        cache_read_tokens=sum(turn.cache_read_tokens for turn in turns),
        cache_creation_tokens=sum(turn.cache_creation_tokens for turn in turns),
        uncached_input_tokens=sum(turn.input_tokens for turn in turns),
        output_tokens=sum(turn.output_tokens for turn in turns),
        cost_usd=total_cost_usd(turns),
        cost_without_cache_usd=cost_without_cache_usd(turns),
        worst_sessions=_worst_sessions(turns, worst_n),
    )


def report_to_dict(report: CacheReport) -> dict:
    """Render a CacheReport as a plain, JSON-serialisable dict."""
    return {
        "window_days": report.window_days,
        "project_filter": report.project_filter,
        "turn_count": report.turn_count,
        "hit_rate": report.hit_rate,
        "tokens": {
            "cache_read": report.cache_read_tokens,
            "cache_creation": report.cache_creation_tokens,
            "uncached_input": report.uncached_input_tokens,
            "output": report.output_tokens,
        },
        "cost_usd": report.cost_usd,
        "cost_without_cache_usd": report.cost_without_cache_usd,
        "worst_sessions": [
            {
                "session_id": session.session_id,
                "project_path": session.project_path,
                "hit_rate": session.hit_rate,
                "cost_usd": session.cost_usd,
            }
            for session in report.worst_sessions
        ],
    }


def render_text(report: CacheReport, console: Console) -> None:
    """Print a CacheReport to the console as a human-readable report."""
    scope = f"last {report.window_days} day(s)"
    if report.project_filter:
        scope += f", project ~ {report.project_filter}"
    console.rule(f"cache-rules — {scope}")

    if report.turn_count == 0:
        console.print("[yellow]No transcript turns found in this window.[/yellow]")
        return

    rate = report.hit_rate
    if rate >= HIT_RATE_TARGET:
        rate_style = "green"
    elif rate >= 0.5:
        rate_style = "yellow"
    else:
        rate_style = "red"

    console.print(f"Cache hit rate : [{rate_style}]{rate:.1%}[/]   (target >90%)")
    console.print(f"Turns          : {report.turn_count:,}")
    console.print(f"Cache reads    : {report.cache_read_tokens:,} tokens")
    console.print(f"Cache writes   : {report.cache_creation_tokens:,} tokens")
    console.print(f"Uncached input : {report.uncached_input_tokens:,} tokens")

    without = report.cost_without_cache_usd
    saved = 1 - report.cost_usd / without if without > 0 else 0.0
    console.print(
        f"Estimated cost : ${report.cost_usd:,.2f}   "
        f"(without cache ${without:,.2f}, saved {saved:.0%})"
    )

    if report.worst_sessions:
        console.print()
        table = Table(title="Lowest hit rate sessions", title_justify="left")
        table.add_column("session")
        table.add_column("project")
        table.add_column("hit rate", justify="right")
        table.add_column("cost", justify="right")
        for session in report.worst_sessions:
            table.add_row(
                session.session_id,
                session.project_path,
                f"{session.hit_rate:.1%}",
                f"${session.cost_usd:,.2f}",
            )
        console.print(table)


def _worst_sessions(turns: list[TranscriptTurn], worst_n: int) -> list[SessionBreakdown]:
    by_session: dict[str, list[TranscriptTurn]] = defaultdict(list)
    for turn in turns:
        by_session[turn.session_id].append(turn)

    breakdowns: list[SessionBreakdown] = []
    for session_id, session_turns in by_session.items():
        total_input = sum(
            turn.cache_read_tokens + turn.cache_creation_tokens + turn.input_tokens
            for turn in session_turns
        )
        if total_input == 0:
            continue  # no cache activity — not an actionable "broken" session
        breakdowns.append(
            SessionBreakdown(
                session_id=session_id,
                project_path=session_turns[0].project_path,
                hit_rate=cache_hit_rate(session_turns),
                cost_usd=total_cost_usd(session_turns),
            )
        )
    breakdowns.sort(key=lambda breakdown: breakdown.hit_rate)
    return breakdowns[:worst_n]
