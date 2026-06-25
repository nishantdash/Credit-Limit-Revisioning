"""L2a — Behavioral model.

Rule-based proxy of the PySpark/Kafka behavioral model described in the brief.
Computes a 0-100 score from utilisation trend, spend velocity, merchant mix and
repayment streak — and emits a directional flag (improving/stable/deteriorating).
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Sequence

from ..models import Card, Transaction


@dataclass
class BehavioralOutput:
    score: float          # 0-100
    direction: str        # IMPROVING / STABLE / DETERIORATING
    utilization_pct: float
    spend_30d: float
    spend_prior_30d: float
    premium_merchant_pct: float
    signals: list[str]


def _bucket_txns(txns: Sequence[Transaction], now: datetime):
    last_30 = [t for t in txns if t.timestamp >= now - timedelta(days=30)]
    prior_30 = [
        t for t in txns
        if now - timedelta(days=60) <= t.timestamp < now - timedelta(days=30)
    ]
    return last_30, prior_30


def score(card: Card, txns: Sequence[Transaction], dpd_max_12m: int) -> BehavioralOutput:
    now = datetime.utcnow()
    last_30, prior_30 = _bucket_txns(txns, now)

    spend_30 = sum(t.amount for t in last_30)
    spend_prior = sum(t.amount for t in prior_30)

    utilization = (card.current_balance / card.current_limit) * 100 if card.current_limit else 0.0
    premium_count = sum(1 for t in last_30 if t.merchant_tier == "PREMIUM")
    premium_pct = (premium_count / len(last_30) * 100) if last_30 else 0.0

    base = 60.0
    signals: list[str] = []

    # Spend velocity
    if spend_prior > 0:
        delta = (spend_30 - spend_prior) / spend_prior
        if delta > 0.25:
            base += 10
            signals.append("SPEND_VELOCITY_UP")
        elif delta < -0.25:
            base -= 12
            signals.append("SPEND_VELOCITY_DOWN")

    # Merchant mix — premium share is a lifestyle-inflation proxy
    if premium_pct > 30:
        base += 8
        signals.append("PREMIUM_MERCHANT_MIX")

    # Utilisation — high sustained util is stress; moderate is healthy
    if utilization > 85:
        base -= 15
        signals.append("HIGH_UTILIZATION")
    elif 30 <= utilization <= 60:
        base += 5
        signals.append("HEALTHY_UTILIZATION")
    elif utilization < 10:
        base -= 5
        signals.append("CARD_USAGE_DECLINING")

    # Repayment streak proxy — uses dpd_max_12m
    if dpd_max_12m == 0:
        base += 12
        signals.append("REPAYMENT_STREAK")
    elif dpd_max_12m > 30:
        base -= 20
        signals.append("PAST_DUE_HISTORY")

    final = max(0.0, min(100.0, base))

    # Direction tag
    if "SPEND_VELOCITY_UP" in signals and "HIGH_UTILIZATION" not in signals:
        direction = "IMPROVING"
    elif "SPEND_VELOCITY_DOWN" in signals or "HIGH_UTILIZATION" in signals or "PAST_DUE_HISTORY" in signals:
        direction = "DETERIORATING"
    else:
        direction = "STABLE"

    return BehavioralOutput(
        score=round(final, 1),
        direction=direction,
        utilization_pct=round(utilization, 1),
        spend_30d=round(spend_30, 2),
        spend_prior_30d=round(spend_prior, 2),
        premium_merchant_pct=round(premium_pct, 1),
        signals=signals,
    )
