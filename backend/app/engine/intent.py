"""Intent disambiguation engine (§3) — the heart of the product.

Answers not "how risky is this customer?" but "what is this customer trying to
do right now, and why?" The problem is non-monotonic and interaction-heavy —
velocity is good *only if* inflow is stable *and* category quality is rising —
so this is an explicit rules-over-features design (the production alternative is
a tree/GBM model). It emits a discrete intent plus a confidence.

Three intents, plus NEUTRAL when nothing fires:
  GROWTH    — high velocity + rising category quality + stable inflow + healthy buffer
  DISTRESS  — velocity + rising min-due dependency + erratic inflow + shrinking buffer
  SEASONAL  — utilisation spike + festive/seasonal context + prepayment behaviour
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import config as cfg_mod
from .signals import SignalBundle

GROWTH = "GROWTH"
DISTRESS = "DISTRESS"
SEASONAL = "SEASONAL"
NEUTRAL = "NEUTRAL"


@dataclass
class IntentOutput:
    intent: str
    confidence: float
    drivers: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)


def _growth_score(s: SignalBundle) -> tuple[float, list[str]]:
    """Growth requires the *conjunction* — a velocity number alone is meaningless,
    but so is stability alone. Without genuine momentum (velocity or up-market
    drift) there is no growth intent, only NEUTRAL."""
    has_momentum = s.velocity_total > 0.12 or s.velocity_discretionary > 0.15 or s.category_drift > 0.015
    if not has_momentum:
        return 0.0, []
    drivers: list[str] = []
    score = 0.0
    if s.velocity_total > 0.25:
        score += 0.25
        drivers.append("VELOCITY_RISING")
    if s.velocity_discretionary > 0.2 and s.category_drift > 0.02:
        score += 0.25
        drivers.append("DISCRETIONARY_LIFT")
    if s.category_quality_index > 0.5 or s.merchant_quality_trend > 0:
        score += 0.15
        drivers.append("CATEGORY_QUALITY_UP")
    if s.inflow_regularity >= 0.7:
        score += 0.20
        drivers.append("STABLE_INFLOW")
    if s.buffer_ratio >= 0.2:
        score += 0.15
        drivers.append("HEALTHY_BUFFER")
    # Hard conditioners: growth is void without stable inflow and a positive buffer.
    if s.inflow_regularity < 0.55 or s.buffer_ratio < 0.05:
        score *= 0.35
    if s.min_due_dependency_rising:
        score *= 0.4  # min-due dependency contradicts genuine growth
    return min(1.0, score), drivers


def _distress_score(s: SignalBundle) -> tuple[float, list[str]]:
    drivers: list[str] = []
    score = 0.0
    if s.min_due_dependency_rising or s.min_due_dependency > 0.7:
        score += 0.30
        drivers.append("MIN_DUE_DEPENDENCY_RISING")
    if s.inflow_regularity < 0.55:
        score += 0.22
        drivers.append("ERRATIC_INFLOW")
    if s.buffer_ratio < 0.05:
        score += 0.22
        drivers.append("SHRINKING_BUFFER")
    if s.utilization > 0.85:
        score += 0.12
        drivers.append("HIGH_UTILIZATION")
    if s.declined_events > 0 and s.buffer_ratio < 0.1:
        score += 0.10
        drivers.append("DECLINES_UNDER_PRESSURE")
    if s.dpd_max_12m >= 1:
        score += 0.10
        drivers.append("RECENT_DPD")
    # A velocity spike *with* these signatures is "plugging a hole", not growth —
    # it amplifies distress rather than mitigating it.
    if s.velocity_total > 0.3 and (s.min_due_dependency_rising or s.buffer_ratio < 0.05):
        score += 0.10
        drivers.append("VELOCITY_PLUGGING_HOLE")
    return min(1.0, score), drivers


def _seasonal_score(s: SignalBundle) -> tuple[float, list[str]]:
    # A genuine seasonal/festive spike is a *necessary* condition — prepayment
    # alone (a dormant customer who clears the tiny balance) is not seasonal.
    spike = s.velocity_total > 0.4 or s.utilization > 0.6
    if not (spike and s.seasonal_context > 0.25):
        return 0.0, []
    drivers: list[str] = ["SEASONAL_SPIKE"]
    score = 0.45
    if s.prepay_behaviour:
        score += 0.30
        drivers.append("HISTORICAL_PREPAYMENT")
    if s.seasonal_context > 0.5:
        score += 0.15
        drivers.append("FESTIVE_CONCENTRATION")
    # Seasonal is void if the customer shows genuine distress — that takes priority.
    # (Buffer is obligation-based, so a festive spike alone won't trip this.)
    if s.min_due_dependency_rising or s.buffer_ratio < -0.1:
        score *= 0.3
    return min(1.0, score), drivers


def classify(sig: SignalBundle, config: cfg_mod.TenantConfig) -> IntentOutput:
    g, g_drv = _growth_score(sig)
    d, d_drv = _distress_score(sig)
    se, se_drv = _seasonal_score(sig)
    scores = {GROWTH: round(g, 3), DISTRESS: round(d, 3), SEASONAL: round(se, 3)}

    # Distress wins ties — the asymmetric cost of missing distress is higher.
    ranked = sorted([(DISTRESS, d), (GROWTH, g), (SEASONAL, se)], key=lambda x: x[1], reverse=True)
    top_intent, top_score = ranked[0]
    second_score = ranked[1][1]

    if top_score < 0.30:
        intent, drivers = NEUTRAL, ["NO_CLEAR_INTENT"]
        confidence = round(0.5 + (0.30 - top_score), 3)  # neutral is "confidently quiet"
    else:
        intent = top_intent
        drivers = {GROWTH: g_drv, DISTRESS: d_drv, SEASONAL: se_drv}[top_intent]
        # Confidence: strength of the winner + separation from the runner-up, then
        # lifted (never lowered) by Layer-4 network embeddedness for growth.
        separation = top_score - second_score
        confidence = 0.45 + 0.4 * top_score + 0.25 * separation
        confidence += 0.1 * sig.income_confidence
        if intent == GROWTH and sig.network_score > 0:
            confidence += 0.1 * sig.network_score   # positive-only network lift (§2.4)
        confidence = round(min(0.99, confidence), 3)

    return IntentOutput(intent=intent, confidence=confidence, drivers=drivers, scores=scores)
