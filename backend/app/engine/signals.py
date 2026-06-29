"""The five signal layers (§2).

Layers 1–3 are retained from the conventional model (made trajectory-sensitive);
Layers 4–5 are the intent-driven additions. Each layer is computed as a set of
closed-form proxies over the card, its 90-day transaction window, and the
AA-sourced cashflow signals. In production these are served from a feature store
fed by PySpark/streaming jobs; here they are deterministic so the demo is
hermetic.

The output `SignalBundle` is the single input to the intent classifier, the
risk model, and the matrix.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Sequence

from ..models import Card, CashflowSignal, Customer, Transaction
from . import config as cfg_mod


# Category-mix "quality" weights (§2.2). A drift toward aspirational lifts the
# index; a drift back to essentials lowers it.
CATEGORY_QUALITY = {"ESSENTIAL": 0.30, "DISCRETIONARY": 0.65, "ASPIRATIONAL": 1.0}
# Categories that imply a seasonal/festive spend (§2.5 / §3.2 Seasonal).
SEASONAL_CATEGORIES = {"TRAVEL_INTL", "TRAVEL_DOM", "LUXURY_RETAIL", "FESTIVE_RETAIL"}

INFLOW_WEIGHTS = {"CBS_SALARY": 1.0, "AA": 0.9, "GST": 0.85, "TRADE": 0.85, "UPI_INFLOW": 0.6}


@dataclass
class SignalBundle:
    # ── Layer 1 — repayment & credit history (trajectory-sensitive) ──
    utilization: float = 0.0
    pqr_level: float = 0.0
    min_due_dependency: float = 0.0      # 0 healthy → 1 paying near minimum
    min_due_dependency_rising: bool = False
    utilization_trend: float = 0.0       # signed: balance-growth proxy
    dpd_max_12m: int = 0
    vintage_months: int = 0

    # ── Layer 2 — behavioural & transactional intent ──
    velocity_total: float = 0.0          # 30d vs prior-30d total-spend acceleration
    velocity_discretionary: float = 0.0  # acceleration in discretionary+aspirational
    category_mix: dict[str, float] = field(default_factory=dict)
    category_quality_index: float = 0.0  # weighted quality of current mix
    category_drift: float = 0.0          # change in quality index vs prior window
    merchant_quality_trend: float = 0.0
    recurrence_score: float = 0.0        # share of recurring/sticky spend
    declined_events: int = 0             # high-value declines against limit

    # ── Layer 3 — stability & fulfilment (AA rail) ──
    income_estimate: float = 0.0
    income_sources: list[str] = field(default_factory=list)
    income_confidence: float = 0.0
    inflow_regularity: float = 0.0       # 0-1 consistency of credits
    buffer_ratio: float = 0.0            # (inflow − outflow) / inflow, live liquidity
    salary_cycle_phase: float = 0.0      # 0-1 position in the pay cycle
    identity_stability: float = 0.85     # positive-only

    # ── Layer 4 — network (positive-only, opt-in) ──
    network_score: float = 0.0           # 0-1; only ever lifts confidence

    # ── Layer 5 — real-time context & liquidity ──
    liquidity_state: float = 0.0         # = buffer_ratio surfaced as a state
    seasonal_context: float = 0.0        # 0-1 strength of festive/seasonal signature
    prepay_behaviour: bool = False       # historically clears balance ahead

    def snapshot(self) -> dict:
        """Compact, explainable view for the audit trail / UI (§6.2)."""
        return {
            "layer1_repayment": {
                "utilization": round(self.utilization, 3),
                "pqr_level": round(self.pqr_level, 3),
                "min_due_dependency": round(self.min_due_dependency, 3),
                "min_due_dependency_rising": self.min_due_dependency_rising,
                "utilization_trend": round(self.utilization_trend, 3),
                "dpd_max_12m": self.dpd_max_12m,
                "vintage_months": self.vintage_months,
            },
            "layer2_behavioural": {
                "velocity_total": round(self.velocity_total, 3),
                "velocity_discretionary": round(self.velocity_discretionary, 3),
                "category_mix": {k: round(v, 2) for k, v in self.category_mix.items()},
                "category_quality_index": round(self.category_quality_index, 3),
                "category_drift": round(self.category_drift, 3),
                "merchant_quality_trend": round(self.merchant_quality_trend, 3),
                "recurrence_score": round(self.recurrence_score, 3),
                "declined_events": self.declined_events,
            },
            "layer3_stability": {
                "income_estimate": round(self.income_estimate, 0),
                "income_sources": self.income_sources,
                "income_confidence": round(self.income_confidence, 2),
                "inflow_regularity": round(self.inflow_regularity, 3),
                "buffer_ratio": round(self.buffer_ratio, 3),
                "salary_cycle_phase": round(self.salary_cycle_phase, 2),
                "identity_stability": round(self.identity_stability, 2),
            },
            "layer4_network": {"network_score": round(self.network_score, 3)},
            "layer5_liquidity": {
                "liquidity_state": round(self.liquidity_state, 3),
                "seasonal_context": round(self.seasonal_context, 3),
                "prepay_behaviour": self.prepay_behaviour,
            },
        }


def _windows(txns: Sequence[Transaction], now: datetime):
    w0 = [t for t in txns if t.timestamp >= now - timedelta(days=30)]
    w1 = [t for t in txns if now - timedelta(days=60) <= t.timestamp < now - timedelta(days=30)]
    w2 = [t for t in txns if now - timedelta(days=90) <= t.timestamp < now - timedelta(days=60)]
    return w0, w1, w2


def _sum(txns: Sequence[Transaction]) -> float:
    return sum(t.amount for t in txns if not t.is_declined)


def _disc_sum(txns: Sequence[Transaction]) -> float:
    return sum(t.amount for t in txns if not t.is_declined and t.category_class in {"DISCRETIONARY", "ASPIRATIONAL"})


def _quality_index(txns: Sequence[Transaction]) -> float:
    spend = _sum(txns)
    if spend <= 0:
        return 0.0
    weighted = sum(t.amount * CATEGORY_QUALITY.get(t.category_class, 0.3)
                   for t in txns if not t.is_declined)
    return weighted / spend


def _mix(txns: Sequence[Transaction]) -> dict[str, float]:
    spend = _sum(txns)
    out = {"ESSENTIAL": 0.0, "DISCRETIONARY": 0.0, "ASPIRATIONAL": 0.0}
    if spend <= 0:
        return out
    for t in txns:
        if t.is_declined:
            continue
        out[t.category_class] = out.get(t.category_class, 0.0) + t.amount
    return {k: v / spend for k, v in out.items()}


def _estimate_income(signals: Sequence[CashflowSignal], stated: float, employment: str):
    if not signals:
        return stated, 0.4, [], 0.5
    if employment == "SALARIED":
        cbs = [s for s in signals if s.source == "CBS_SALARY"]
        if cbs:
            anchor = max(s.monthly_amount for s in cbs)
            corr = [s for s in signals if s.source in {"AA", "UPI_INFLOW"}]
            if corr:
                blended = anchor * 0.7 + (sum(s.monthly_amount for s in corr) / len(corr)) * 0.3
                conf = 0.9
            else:
                blended, conf = anchor, 0.75
            sources = sorted({s.source for s in [*cbs, *corr]})
            reg = sum(s.regularity for s in [*cbs, *corr]) / len(cbs + corr)
            return blended, conf, sources, reg
    num = den = 0.0
    for s in signals:
        w = INFLOW_WEIGHTS.get(s.source, 0.5)
        num += s.monthly_amount * w
        den += w
    blended = num / den if den else stated
    conf = min(0.95, 0.5 + 0.1 * len({s.source for s in signals}))
    reg = sum(s.regularity for s in signals) / len(signals)
    return blended, conf, sorted({s.source for s in signals}), reg


def compute(
    customer: Customer,
    card: Card,
    txns: Sequence[Transaction],
    signals: Sequence[CashflowSignal],
    config: cfg_mod.TenantConfig,
    now: datetime | None = None,
) -> SignalBundle:
    now = now or datetime.utcnow()
    w0, w1, w2 = _windows(txns, now)

    b = SignalBundle()

    # ── Layer 1 ─────────────────────────────────────────────
    b.utilization = (card.outstanding / card.current_limit) if card.current_limit else 0.0
    b.pqr_level = (card.last_payment / card.statement_balance) if card.statement_balance else 1.0
    b.pqr_level = max(0.0, min(1.5, b.pqr_level))
    b.min_due_dependency = min(1.0, card.min_due_last / max(card.last_payment, 1.0)) if card.last_payment else 1.0
    b.dpd_max_12m = customer.dpd_max_12m or 0
    b.vintage_months = customer.account_vintage_months or 0

    spend0, spend1, spend2 = _sum(w0), _sum(w1), _sum(w2)
    # Utilisation trend proxy = essential-spend growth (balance is built on essentials).
    ess0 = sum(t.amount for t in w0 if t.category_class == "ESSENTIAL" and not t.is_declined)
    ess1 = sum(t.amount for t in w1 if t.category_class == "ESSENTIAL" and not t.is_declined)
    b.utilization_trend = ((spend0 - spend1) / spend1) if spend1 else 0.0
    # Min-due dependency is "rising" if the customer leans on minimums while
    # utilisation and essential spend climb — the early distress signature.
    b.min_due_dependency_rising = (
        b.min_due_dependency > 0.6 and (b.utilization > 0.55 or (ess0 > ess1 * 1.1 and b.pqr_level < 0.4))
    )

    # ── Layer 2 ─────────────────────────────────────────────
    b.velocity_total = ((spend0 - spend1) / spend1) if spend1 else 0.0
    disc0, disc1 = _disc_sum(w0), _disc_sum(w1)
    b.velocity_discretionary = ((disc0 - disc1) / disc1) if disc1 else (1.0 if disc0 > 0 else 0.0)
    b.category_mix = _mix(w0)
    q0, q1 = _quality_index(w0), _quality_index(w1)
    b.category_quality_index = q0
    b.category_drift = q0 - q1
    mq0 = (sum(t.merchant_quality for t in w0 if not t.is_declined) / len([t for t in w0 if not t.is_declined])) if [t for t in w0 if not t.is_declined] else 0.6
    mq1 = (sum(t.merchant_quality for t in w1 if not t.is_declined) / len([t for t in w1 if not t.is_declined])) if [t for t in w1 if not t.is_declined] else mq0
    b.merchant_quality_trend = mq0 - mq1
    rec = [t for t in w0 if t.is_recurring]
    b.recurrence_score = (sum(t.amount for t in rec) / spend0) if spend0 else 0.0
    b.declined_events = sum(1 for t in w0 if t.is_declined)

    # ── Layer 3 ─────────────────────────────────────────────
    income, conf, sources, reg = _estimate_income(signals, customer.stated_income, customer.employment_type)
    b.income_estimate = income
    b.income_confidence = conf
    b.income_sources = sources
    b.inflow_regularity = reg if customer.aa_consent_active else min(reg, 0.5)
    # Buffer reflects *sustained* obligations, not a one-off discretionary spike — a
    # festive splurge must not read as a shrinking buffer. Obligations = essential +
    # recurring spend + minimum due + external debt.
    recurring_nonessential = sum(
        t.amount for t in w0
        if t.is_recurring and t.category_class != "ESSENTIAL" and not t.is_declined
    )
    obligations = ess0 + recurring_nonessential + (card.min_due_last or 0) + (customer.external_debt or 0)
    b.buffer_ratio = max(-1.0, min(1.0, (income - obligations) / income)) if income else 0.0
    b.salary_cycle_phase = 0.5  # neutral without precise pay-date telemetry
    b.identity_stability = 0.85

    # ── Layer 4 — positive-only, opt-in (§2.4) ──────────────
    if config.network_enabled:
        # Verifiable, regular counterparties (employer / trade partners) lift confidence.
        verifiable = [s for s in signals if s.source in {"CBS_SALARY", "TRADE", "GST"}]
        if verifiable:
            b.network_score = min(1.0, sum(s.regularity for s in verifiable) / len(verifiable))
    # never penalises — clamped to [0, 1], only used additively

    # ── Layer 5 ─────────────────────────────────────────────
    b.liquidity_state = b.buffer_ratio
    seasonal0 = sum(t.amount for t in w0 if t.merchant_category in SEASONAL_CATEGORIES and not t.is_declined)
    seasonal_share = (seasonal0 / spend0) if spend0 else 0.0
    spike = b.velocity_total > 0.4
    b.prepay_behaviour = b.pqr_level >= 0.9 and b.dpd_max_12m == 0
    # Seasonal signature: a spike concentrated in seasonal categories by a customer
    # who historically prepays — the Input-C case in §3.3.
    b.seasonal_context = min(1.0, seasonal_share * (1.3 if spike else 0.6) * (1.2 if b.prepay_behaviour else 0.7))

    return b
