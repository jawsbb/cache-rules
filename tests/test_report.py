from __future__ import annotations

import io
import json
from datetime import UTC, datetime

from rich.console import Console

from cache_rules.checks.base import CheckResult, Severity
from cache_rules.metrics.cost import cost_without_cache_usd, total_cost_usd
from cache_rules.parser.transcripts import TranscriptTurn
from cache_rules.report.renderer import (
    build_cache_report,
    render_check_results,
    render_text,
    report_to_dict,
)

NOW = datetime(2026, 5, 22, 12, 0, 0, tzinfo=UTC)


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


def test_build_cache_report_summarises_token_usage_and_cost() -> None:
    turns = [
        _turn(input_tokens=100, cache_creation_tokens=300, cache_read_tokens=600, output_tokens=50),
        _turn(cache_read_tokens=1000, output_tokens=10),
    ]

    report = build_cache_report(turns, window_days=7, project_filter=None, now=NOW)

    assert report.turn_count == 2
    assert report.hit_rate == 0.8  # 1600 cached / 2000 total input
    assert report.cache_read_tokens == 1600
    assert report.cache_creation_tokens == 300
    assert report.uncached_input_tokens == 100
    assert report.output_tokens == 60
    assert report.cost_usd == total_cost_usd(turns)
    assert report.window_days == 7
    assert report.project_filter is None


def test_build_cache_report_keeps_only_turns_inside_window_and_project() -> None:
    turns = [
        _turn(  # inside window, project alpha
            timestamp=datetime(2026, 5, 21, 9, 0, 0, tzinfo=UTC),
            project_path="/code/alpha",
            cache_read_tokens=10,
        ),
        _turn(  # too old — outside the 7-day window
            timestamp=datetime(2026, 5, 1, 9, 0, 0, tzinfo=UTC),
            project_path="/code/alpha",
            cache_read_tokens=10,
        ),
        _turn(  # inside window, project beta
            timestamp=datetime(2026, 5, 21, 9, 0, 0, tzinfo=UTC),
            project_path="/code/beta",
            cache_read_tokens=10,
        ),
    ]

    no_filter = build_cache_report(turns, window_days=7, project_filter=None, now=NOW)
    assert no_filter.turn_count == 2  # both recent turns, old one dropped

    alpha = build_cache_report(turns, window_days=7, project_filter="alpha", now=NOW)
    assert alpha.turn_count == 1  # only the recent alpha turn


def test_build_cache_report_ranks_worst_sessions_by_hit_rate() -> None:
    turns = [
        _turn(session_id="bad", project_path="/x", cache_read_tokens=100, input_tokens=900),
        _turn(session_id="mid", project_path="/y", cache_read_tokens=500, input_tokens=500),
        _turn(session_id="good", project_path="/z", cache_read_tokens=900, input_tokens=100),
        _turn(session_id="empty", project_path="/w", output_tokens=50),  # no input tokens
    ]

    report = build_cache_report(turns, window_days=7, project_filter=None, now=NOW)

    # ascending hit rate; the input-less "empty" session is not actionable, so excluded
    assert [s.session_id for s in report.worst_sessions] == ["bad", "mid", "good"]
    assert report.worst_sessions[0].hit_rate == 0.1
    assert report.worst_sessions[0].project_path == "/x"

    capped = build_cache_report(turns, window_days=7, project_filter=None, now=NOW, worst_n=2)
    assert [s.session_id for s in capped.worst_sessions] == ["bad", "mid"]


def test_build_cache_report_includes_cost_without_cache() -> None:
    turns = [
        _turn(input_tokens=100, cache_creation_tokens=300, cache_read_tokens=600, output_tokens=50),
    ]
    report = build_cache_report(turns, window_days=7, project_filter=None, now=NOW)
    assert report.cost_without_cache_usd == cost_without_cache_usd(turns)
    assert report.cost_without_cache_usd > report.cost_usd


def test_report_to_dict_is_json_serialisable_with_expected_shape() -> None:
    turns = [
        _turn(
            session_id="x",
            project_path="/proj/x",
            input_tokens=900,
            cache_read_tokens=100,
            output_tokens=20,
        ),
    ]
    report = build_cache_report(turns, window_days=14, project_filter="proj", now=NOW)

    payload = report_to_dict(report)

    assert json.loads(json.dumps(payload)) == payload  # round-trips through JSON
    assert payload["window_days"] == 14
    assert payload["project_filter"] == "proj"
    assert payload["turn_count"] == 1
    assert payload["hit_rate"] == 0.1
    assert payload["tokens"]["cache_read"] == 100
    assert payload["worst_sessions"][0]["session_id"] == "x"


def _render(report) -> str:
    out = io.StringIO()
    render_text(report, Console(file=out, width=100))
    return out.getvalue()


def test_render_text_shows_headline_numbers() -> None:
    turns = [
        _turn(session_id="broken", project_path="/repo", input_tokens=900, cache_read_tokens=100),
    ]
    report = build_cache_report(turns, window_days=7, project_filter=None, now=NOW)

    text = _render(report)

    assert "cache-rules" in text  # header
    assert "10.0%" in text  # hit rate
    assert "broken" in text  # worst session surfaced


def test_render_text_handles_an_empty_window() -> None:
    report = build_cache_report([], window_days=7, project_filter=None, now=NOW)

    assert "No transcript turns" in _render(report)


def test_render_check_results_shows_each_rule_with_its_verdict() -> None:
    results = [
        CheckResult(4, "Model switching", Severity.PASS, "No model switching detected."),
        CheckResult(6, "Fork safety", Severity.MANUAL, "Review manually.", fix="reuse the prefix"),
    ]
    out = io.StringIO()

    render_check_results(results, Console(file=out, width=100))
    text = out.getvalue()

    assert "Model switching" in text
    assert "Fork safety" in text
    assert "PASS" in text
    assert "MANUAL" in text
    assert "reuse the prefix" in text  # the fix is shown
