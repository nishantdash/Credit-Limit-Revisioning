"""Risk model — PD prior + dynamic risk tiers (§3.1, §4.1).

The conventional logistic PD model is retained but demoted to a *prior*, not the
decision-maker. PD maps to one of four dynamic tiers, evaluated continuously.
The hard-knockout layer can place an account in Tier 4 directly (handled in the
orchestrator), bypassing this scorer.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import config as cfg_mod
from .signals import SignalBundle


@dataclass
class RiskOutput:
    pd_pre: float
    pd_post_projected: float
    tier: int
    feature_contributions: dict[str, float] = field(default_factory=dict)


def _logistic(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))


def _pd(bureau: int, sig: SignalBundle, current_limit: float, projected_limit: float,
        income: float) -> tuple[float, float, dict[str, float]]:
    # Each feature contributes to log-odds; larger positive = riskier.
    f_bureau = (750 - bureau) / 80.0
    f_pqr = (0.6 - sig.pqr_level) * 1.4
    f_min_due = (sig.min_due_dependency - 0.4) * 1.3
    f_dpd = (sig.dpd_max_12m / 30.0) * 1.2
    f_util = max(0.0, (sig.utilization - 0.6) / 0.4) * 0.6
    f_buffer = min(0.9, max(0.0, (0.15 - sig.buffer_ratio)) * 1.6)
    f_income_pre = max(0.0, current_limit / max(1.0, income) - 3.0) * 0.5
    f_income_post = max(0.0, projected_limit / max(1.0, income) - 3.0) * 0.5

    base = -4.0
    z_pre = base + f_bureau + f_pqr + f_min_due + f_dpd + f_util + f_buffer + f_income_pre
    z_post = base + f_bureau + f_pqr + f_min_due + f_dpd + f_util + f_buffer + f_income_post
    contribs = {
        "bureau": round(f_bureau, 3),
        "pqr": round(f_pqr, 3),
        "min_due_dependency": round(f_min_due, 3),
        "dpd": round(f_dpd, 3),
        "utilization": round(f_util, 3),
        "buffer": round(f_buffer, 3),
        "income_vs_limit": round(f_income_post, 3),
    }
    return _logistic(z_pre), _logistic(z_post), contribs


def assign_tier(pd: float, config: cfg_mod.TenantConfig) -> int:
    bands = config.tier_pd_bands
    if pd < bands["tier1"]:
        return 1
    if pd < bands["tier2"]:
        return 2
    if pd < bands["tier3"]:
        return 3
    return 4


def score(
    *,
    bureau_score: int,
    sig: SignalBundle,
    current_limit: float,
    projected_limit: float,
    config: cfg_mod.TenantConfig,
) -> RiskOutput:
    pd_pre, pd_post, contribs = _pd(
        bureau_score, sig, current_limit, projected_limit, sig.income_estimate
    )
    return RiskOutput(
        pd_pre=round(pd_pre, 4),
        pd_post_projected=round(pd_post, 4),
        tier=assign_tier(pd_pre, config),
        feature_contributions=contribs,
    )
