from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

from cache_rules.parser.transcripts import TranscriptTurn


class Severity(Enum):
    """Outcome of a single rule check."""

    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    MANUAL = "manual"


@dataclass(frozen=True, slots=True)
class CheckResult:
    """The verdict of one rule check, with evidence and a concrete fix."""

    rule_id: int
    rule_name: str
    severity: Severity
    message: str
    evidence: dict = field(default_factory=dict)
    fix: str | None = None


@dataclass(frozen=True, slots=True)
class AuditContext:
    """Everything a check needs to run.

    Starts with parsed transcript turns; settings.json / CLAUDE.md / hooks are
    added as the checks that need them are implemented.
    """

    turns: list[TranscriptTurn]


class Check(Protocol):
    """A single prompt-cache rule check."""

    rule_id: int
    rule_name: str

    def run(self, ctx: AuditContext) -> CheckResult: ...
