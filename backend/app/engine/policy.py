"""L3a — Bank-configurable policy rules engine.

Each rule returns a tuple (passes: bool, reason_code: str | None). The decision
engine treats any failure as a hard veto on UPGRADE — these are the guardrails
the AI can never override (RBI / bank credit-policy team owns them).
"""
from dataclasses import dataclass


@dataclass
class PolicyConfig:
    max_limit_multiple_of_income: float = 3.0
    hitl_threshold_inr: float = 50_000.0
    min_months_at_current_limit: int = 6
    max_dpd_eligible_12m: int = 60
    pd_threshold_upgrade: float = 0.05
    auto_freeze_pd: float = 0.08


@dataclass
class PolicyCheckResult:
    passes: bool
    violated_codes: list[str]


def check_upgrade_eligibility(
    *,
    config: PolicyConfig,
    proposed_limit: float,
    income_estimate: float,
    dpd_max_12m: int,
    months_at_current_limit: int,
    pd_post: float,
) -> PolicyCheckResult:
    violated: list[str] = []

    if dpd_max_12m > config.max_dpd_eligible_12m:
        violated.append("POLICY_VIOLATION_DPD")
    if months_at_current_limit < config.min_months_at_current_limit:
        violated.append("POLICY_VIOLATION_TENURE")
    if income_estimate > 0 and proposed_limit > income_estimate * config.max_limit_multiple_of_income:
        violated.append("POLICY_VIOLATION_INCOME_CAP")
    if pd_post > config.pd_threshold_upgrade:
        violated.append("PD_OVER_THRESHOLD")

    return PolicyCheckResult(passes=not violated, violated_codes=violated)


def requires_hitl(*, limit_delta_inr: float, config: PolicyConfig) -> bool:
    return abs(limit_delta_inr) > config.hitl_threshold_inr
