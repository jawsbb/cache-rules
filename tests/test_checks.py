from __future__ import annotations

from datetime import UTC, datetime

from cache_rules.checks.base import AuditContext, Severity
from cache_rules.checks.registry import ALL_CHECKS
from cache_rules.checks.rule4_models import ModelSwitchingCheck
from cache_rules.checks.rule6_forks import ForkSafetyCheck
from cache_rules.parser.transcripts import TranscriptTurn


def _turn(
    *,
    session_id: str = "s1",
    model: str = "claude-opus-4-7",
    is_sidechain: bool = False,
    input_tokens: int = 0,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> TranscriptTurn:
    return TranscriptTurn(
        timestamp=datetime(2026, 5, 21, 12, 0, 0, tzinfo=UTC),
        session_id=session_id,
        project_path="/p",
        model=model,
        input_tokens=input_tokens,
        cache_creation_tokens=cache_creation_tokens,
        cache_read_tokens=cache_read_tokens,
        output_tokens=0,
        is_sidechain=is_sidechain,
    )


def test_rule4_passes_when_each_session_uses_one_model() -> None:
    turns = [
        _turn(session_id="a", model="claude-opus-4-7"),
        _turn(session_id="a", model="claude-opus-4-7"),
        _turn(session_id="b", model="claude-sonnet-4-6"),
    ]

    result = ModelSwitchingCheck().run(AuditContext(turns=turns))

    assert result.rule_id == 4
    assert result.severity is Severity.PASS


def test_rule4_fails_when_a_session_switches_models() -> None:
    turns = [
        _turn(session_id="mixed", model="claude-opus-4-7"),
        _turn(session_id="mixed", model="claude-sonnet-4-6"),
        _turn(session_id="clean", model="claude-opus-4-7"),
    ]

    result = ModelSwitchingCheck().run(AuditContext(turns=turns))

    assert result.severity is Severity.FAIL
    assert result.evidence["sessions"]["mixed"] == [
        "claude-opus-4-7",
        "claude-sonnet-4-6",
    ]
    assert "clean" not in result.evidence["sessions"]
    assert result.fix is not None


def test_rule4_ignores_synthetic_model_turns() -> None:
    # <synthetic> turns are local, not real API calls — they must not look like a switch
    turns = [
        _turn(session_id="s", model="claude-opus-4-7"),
        _turn(session_id="s", model="<synthetic>"),
    ]

    result = ModelSwitchingCheck().run(AuditContext(turns=turns))

    assert result.severity is Severity.PASS


def test_rule4_passes_on_an_empty_context() -> None:
    result = ModelSwitchingCheck().run(AuditContext(turns=[]))

    assert result.severity is Severity.PASS


def test_rule4_ignores_sidechain_subagent_turns() -> None:
    # a subagent (sidechain) shares the parent sessionId but runs in its own cache
    # context; running it on a cheaper model is not a main-thread model switch
    turns = [
        _turn(session_id="s", model="claude-opus-4-7", is_sidechain=False),
        _turn(session_id="s", model="claude-haiku-4-5", is_sidechain=True),
    ]

    result = ModelSwitchingCheck().run(AuditContext(turns=turns))

    assert result.severity is Severity.PASS


def test_rule6_is_manual_and_reports_sidechain_evidence() -> None:
    turns = [
        _turn(is_sidechain=False, cache_read_tokens=900, input_tokens=100),
        _turn(is_sidechain=True, cache_read_tokens=300, cache_creation_tokens=700),
        _turn(is_sidechain=True, cache_read_tokens=100, cache_creation_tokens=900),
    ]

    result = ForkSafetyCheck().run(AuditContext(turns=turns))

    assert result.rule_id == 6
    assert result.severity is Severity.MANUAL
    assert result.evidence["sidechain_turns"] == 2
    # 400 cached reads / 2000 total input across the two sidechain turns
    assert result.evidence["sidechain_hit_rate"] == 0.2


def test_registry_lists_every_implemented_check() -> None:
    rule_ids = sorted(check.rule_id for check in ALL_CHECKS)
    assert rule_ids == [4, 6]
