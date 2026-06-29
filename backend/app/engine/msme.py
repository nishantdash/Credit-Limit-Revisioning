"""MSME double-gate (§9).

Salaried individuals and businesses have fundamentally different risk structures.
For MSMEs the promoter's personal finances and the business are intertwined, so
the engine scores both and fuses them:

    Final_Grade = f(Promoter_Personal_Score, Business_Financial_&_Trade_Score)

The genuine information edge: a business signals distress to its *vendors* before
its bank — so trade-credit DPD is weighted as a *primary*, real-time trigger.
A specific pattern only the fused view catches: promoter personal spend spikes
while the business working-capital line maxes out.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..models import Customer
from .signals import SignalBundle


@dataclass
class MsmeOutput:
    business_score: float          # 0-100
    promoter_score: float          # 0-100
    final_grade: float             # 0-100 fused
    trade_distress: bool           # trade-credit early warning fired
    intent_override: str | None    # forces DISTRESS when the fused pattern appears
    drivers: list[str] = field(default_factory=list)


def evaluate(customer: Customer, sig: SignalBundle) -> MsmeOutput:
    drivers: list[str] = []

    # Business gate — DSCR, working-capital utilisation, and trade-credit DPD.
    dscr = customer.dscr if customer.dscr is not None else 1.2
    wc_util = customer.working_capital_utilization if customer.working_capital_utilization is not None else 0.5
    trade_dpd = customer.trade_dpd_days or 0

    business = 60.0
    business += min(25.0, (dscr - 1.0) * 40.0)        # DSCR > 1 is healthy
    business -= max(0.0, (wc_util - 0.7)) * 60.0       # maxed working capital is stress
    if trade_dpd > 0:
        business -= min(40.0, trade_dpd * 1.5)
        drivers.append("TRADE_CREDIT_DPD")
    business = max(0.0, min(100.0, business))

    # Promoter gate — personal-side score (reuse the retail signal bundle as proxy).
    promoter = customer.promoter_score
    if promoter is None:
        promoter = 50.0 + 30.0 * sig.inflow_regularity + 15.0 * (1.0 if sig.buffer_ratio > 0.15 else 0.0)
        promoter = max(0.0, min(100.0, promoter))

    # Fusion — weight trade deterioration as primary (forward signal).
    final = 0.55 * business + 0.45 * promoter
    trade_distress = trade_dpd >= 15

    # The nameable fused pattern: promoter personal spend spikes while the business
    # working-capital line maxes out. Neither gate alone sees it.
    intent_override = None
    if sig.velocity_total > 0.3 and wc_util > 0.85:
        intent_override = "DISTRESS"
        drivers.append("PROMOTER_SPEND_VS_MAXED_WORKING_CAPITAL")
    elif trade_distress:
        intent_override = "DISTRESS"

    return MsmeOutput(
        business_score=round(business, 1),
        promoter_score=round(promoter, 1),
        final_grade=round(final, 1),
        trade_distress=trade_distress,
        intent_override=intent_override,
        drivers=drivers,
    )
