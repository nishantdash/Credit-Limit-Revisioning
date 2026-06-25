"""L2c — Risk scorer.

Produces Probability of Default (PD) from bureau + behavioral + income signals.
Prototype uses a logistic-style closed form in place of XGBoost; the SHAP-style
reason-code list is computed by ranking contribution of each feature.
"""
from dataclasses import dataclass
import math


@dataclass
class RiskOutput:
    pd_pre: float           # probability of default at current limit
    pd_post_projected: float
    feature_contributions: dict[str, float]


def _logistic(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))


def score(
    bureau_score: int,
    behavioral_score: float,
    income_estimate: float,
    current_limit: float,
    projected_limit: float,
    dpd_max_12m: int,
    utilization_pct: float,
) -> RiskOutput:
    # Map each input to a contribution; bigger positive = more risky.
    # Bureau 300..900 → centred at 750
    f_bureau = (750 - bureau_score) / 80.0
    # Behavioral 0..100 → centred at 65
    f_behavior = (65 - behavioral_score) / 25.0
    # Income vs limit ratio — limit > 3x income is risky
    income_ratio_pre = current_limit / max(1.0, income_estimate)
    income_ratio_post = projected_limit / max(1.0, income_estimate)
    f_income_pre = max(0.0, income_ratio_pre - 2.0) * 0.6
    f_income_post = max(0.0, income_ratio_post - 2.0) * 0.6
    # DPD
    f_dpd = (dpd_max_12m / 30.0) * 1.2
    # Utilisation
    f_util = max(0.0, (utilization_pct - 60) / 40.0) * 0.5

    z_pre = -3.0 + f_bureau + f_behavior + f_income_pre + f_dpd + f_util
    z_post = -3.0 + f_bureau + f_behavior + f_income_post + f_dpd + f_util

    pd_pre = _logistic(z_pre)
    pd_post = _logistic(z_post)

    contribs = {
        "bureau_score": round(f_bureau, 3),
        "behavioral_score": round(f_behavior, 3),
        "income_vs_limit": round(f_income_post, 3),
        "dpd_max_12m": round(f_dpd, 3),
        "utilization": round(f_util, 3),
    }
    return RiskOutput(
        pd_pre=round(pd_pre, 4),
        pd_post_projected=round(pd_post, 4),
        feature_contributions=contribs,
    )
