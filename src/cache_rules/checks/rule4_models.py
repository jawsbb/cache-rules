from __future__ import annotations

from collections import defaultdict

from cache_rules.checks.base import AuditContext, CheckResult, Severity

# Claude Code records locally-generated assistant messages with this model id;
# they are not real API calls and must not count as a model switch.
SYNTHETIC_MODEL = "<synthetic>"


class ModelSwitchingCheck:
    """Rule 4 — a conversation thread should never switch models.

    Only main-thread turns count. Sidechain (subagent) turns share the parent
    sessionId but run in their own cache context, so a subagent on a cheaper
    model is expected, not a switch.
    """

    rule_id = 4
    rule_name = "Model switching"

    def run(self, ctx: AuditContext) -> CheckResult:
        models_by_session: dict[str, set[str]] = defaultdict(set)
        for turn in ctx.turns:
            if turn.is_sidechain or turn.model == SYNTHETIC_MODEL:
                continue
            models_by_session[turn.session_id].add(turn.model)

        offenders = {
            session_id: sorted(models)
            for session_id, models in models_by_session.items()
            if len(models) > 1
        }

        if offenders:
            return CheckResult(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                severity=Severity.FAIL,
                message=f"{len(offenders)} session(s) switched models mid-conversation.",
                evidence={"sessions": offenders},
                fix="Keep one model per conversation thread — a model switch starts a "
                "fresh cache and discards the existing prefix.",
            )

        return CheckResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            severity=Severity.PASS,
            message="No model switching detected.",
        )
