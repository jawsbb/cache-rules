from __future__ import annotations

from cache_rules.checks.base import Check
from cache_rules.checks.rule4_models import ModelSwitchingCheck
from cache_rules.checks.rule6_forks import ForkSafetyCheck

# Every implemented check. Rules 1, 2, 3 and 5 are added as their data
# sources (config files, hooks, tool lists) become available.
ALL_CHECKS: list[Check] = [
    ModelSwitchingCheck(),
    ForkSafetyCheck(),
]
