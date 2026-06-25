"""L2b — Income estimator.

Triangulates CBS_SALARY + UPI_INFLOW + AA + GST signals (per the brief) into a
single estimated monthly income with a confidence band.
"""
from dataclasses import dataclass
from typing import Sequence

from ..models import IncomeSignal


# Trust weights per source for triangulation.
WEIGHTS = {
    "CBS_SALARY": 1.0,   # most trustworthy for salaried
    "AA": 0.9,           # consented bank-account cashflow
    "GST": 0.85,         # declared business income
    "UPI_INFLOW": 0.6,   # noisy, includes transfers
}


@dataclass
class IncomeOutput:
    estimate_inr: float
    confidence: float       # 0-1
    sources_used: list[str]
    delta_vs_stated_pct: float


def estimate(signals: Sequence[IncomeSignal], stated_income: float, employment_type: str) -> IncomeOutput:
    if not signals:
        return IncomeOutput(
            estimate_inr=stated_income,
            confidence=0.4,
            sources_used=[],
            delta_vs_stated_pct=0.0,
        )

    # For salaried customers, prefer CBS_SALARY if present.
    if employment_type == "SALARIED":
        cbs = [s for s in signals if s.source == "CBS_SALARY"]
        if cbs:
            anchor = max(s.monthly_amount for s in cbs)
            corroborators = [s for s in signals if s.source in {"AA", "UPI_INFLOW"}]
            if corroborators:
                blended = anchor * 0.7 + (sum(s.monthly_amount for s in corroborators) / len(corroborators)) * 0.3
                conf = 0.9
            else:
                blended = anchor
                conf = 0.75
            sources = sorted({s.source for s in [*cbs, *corroborators]})
            delta = ((blended - stated_income) / stated_income * 100) if stated_income else 0.0
            return IncomeOutput(round(blended, 2), conf, sources, round(delta, 1))

    # Self-employed (or salaried with no CBS_SALARY): weighted average.
    num, den = 0.0, 0.0
    for s in signals:
        w = WEIGHTS.get(s.source, 0.5)
        num += s.monthly_amount * w
        den += w
    blended = num / den if den else stated_income
    confidence = min(0.95, 0.5 + 0.1 * len({s.source for s in signals}))
    sources = sorted({s.source for s in signals})
    delta = ((blended - stated_income) / stated_income * 100) if stated_income else 0.0
    return IncomeOutput(round(blended, 2), round(confidence, 2), sources, round(delta, 1))
