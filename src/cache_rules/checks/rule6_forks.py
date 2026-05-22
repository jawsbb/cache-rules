from __future__ import annotations

from cache_rules.checks.base import AuditContext, CheckResult, Severity
from cache_rules.metrics.cache import cache_hit_rate


class ForkSafetyCheck:
    """Rule 6 — compaction and subagent forks should reuse the parent's cached prefix.

    This cannot be fully verified from transcripts yet, so the verdict is MANUAL.
    The evidence reports how sidechain (subagent) turns are caching, which is the
    starting point for a manual review.
    """

    rule_id = 6
    rule_name = "Fork safety"

    def run(self, ctx: AuditContext) -> CheckResult:
        sidechain_turns = [turn for turn in ctx.turns if turn.is_sidechain]
        return CheckResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            severity=Severity.MANUAL,
            message=(
                "Fork safety can't be auto-verified from transcripts yet — "
                "review subagent and compaction cache behaviour manually."
            ),
            evidence={
                "sidechain_turns": len(sidechain_turns),
                "sidechain_hit_rate": cache_hit_rate(sidechain_turns),
            },
            fix=(
                "A spawned subagent or a compacted context should reuse the parent's "
                "cached prefix where possible. Compare the sidechain hit rate against "
                "the main thread — a large gap means forks are paying for fresh cache."
            ),
        )
