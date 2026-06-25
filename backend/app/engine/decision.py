"""L3b — Limit calculator and end-to-end decision orchestration.

Pulls all the L2 outputs together, applies L3a policy rules, derives the
optimal recommended limit, attaches reason codes and explainer text, and
writes the Decision + AuditLog rows.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ..models import AuditLog, Card, Customer, Decision, IncomeSignal, Transaction
from . import behavioral, explainer, income, policy, risk


BENEFITS_TIERS = ["SILVER", "GOLD", "PLATINUM"]
TIER_LIMIT_BANDS = [
    (0, 100_000, "SILVER"),
    (100_000, 250_000, "GOLD"),
    (250_000, 10_000_000, "PLATINUM"),
]


def tier_for_limit(limit: float) -> str:
    for lo, hi, tier in TIER_LIMIT_BANDS:
        if lo <= limit < hi:
            return tier
    return BENEFITS_TIERS[-1]


@dataclass
class DecisionContext:
    customer: Customer
    card: Card
    trigger_type: str
    policy_config: policy.PolicyConfig


def _optimal_upgrade_limit(income_estimate: float, current_limit: float, config: policy.PolicyConfig) -> float:
    """Pick the optimal target limit: income-cap-bounded, smoothed for stability."""
    income_cap = income_estimate * config.max_limit_multiple_of_income
    aggressive = current_limit * 1.6
    moderate = current_limit + 50_000
    target = min(income_cap, max(moderate, aggressive))
    target = round(target / 5000) * 5000  # round to nearest 5k
    return max(target, current_limit)


def _downgrade_limit(current_limit: float, income_estimate: float) -> float:
    target = min(current_limit * 0.75, income_estimate * 2.0)
    target = round(target / 5000) * 5000
    return max(target, 10_000)


def decide(
    db: Session,
    *,
    customer_id: str,
    trigger_type: str,
    policy_config: Optional[policy.PolicyConfig] = None,
) -> Decision:
    config = policy_config or policy.PolicyConfig()
    customer: Customer = db.query(Customer).filter(Customer.id == customer_id).one()
    card: Card = customer.cards[0]
    txns = db.query(Transaction).filter(Transaction.card_id == card.id).all()
    income_signals = db.query(IncomeSignal).filter(IncomeSignal.customer_id == customer.id).all()

    # L2a behavioral
    beh = behavioral.score(card, txns, customer.dpd_max_12m)
    # L2b income
    inc = income.estimate(income_signals, customer.stated_income, customer.employment_type)
    # L2c risk — first compute against current limit
    risk_pre = risk.score(
        bureau_score=customer.bureau_score,
        behavioral_score=beh.score,
        income_estimate=inc.estimate_inr,
        current_limit=card.current_limit,
        projected_limit=card.current_limit,
        dpd_max_12m=customer.dpd_max_12m,
        utilization_pct=beh.utilization_pct,
    )

    # Decision direction
    reason_codes: list[str] = []
    if beh.direction == "DETERIORATING" or risk_pre.pd_pre > config.auto_freeze_pd:
        decision_type = "DOWNGRADE"
        recommended = _downgrade_limit(card.current_limit, inc.estimate_inr)
        reason_codes.extend([s for s in beh.signals if s in {"SPEND_VELOCITY_DOWN", "HIGH_UTILIZATION", "PAST_DUE_HISTORY", "CARD_USAGE_DECLINING"}])
        if not reason_codes:
            reason_codes.append("HIGH_UTILIZATION")
    elif beh.direction == "IMPROVING" and inc.estimate_inr > customer.stated_income * 1.05:
        decision_type = "UPGRADE"
        recommended = _optimal_upgrade_limit(inc.estimate_inr, card.current_limit, config)
        if inc.delta_vs_stated_pct > 5:
            reason_codes.append("INCOME_GROWTH")
        if customer.dpd_max_12m == 0:
            reason_codes.append("REPAYMENT_STREAK")
        for s in beh.signals:
            if s in {"PREMIUM_MERCHANT_MIX", "SPEND_VELOCITY_UP", "HEALTHY_UTILIZATION"}:
                reason_codes.append(s)
    else:
        decision_type = "FREEZE"
        recommended = card.current_limit
        for s in beh.signals:
            reason_codes.append(s)
        if not reason_codes:
            reason_codes.append("UTILIZATION_STABLE")

    # Re-run risk against the projected limit
    risk_post = risk.score(
        bureau_score=customer.bureau_score,
        behavioral_score=beh.score,
        income_estimate=inc.estimate_inr,
        current_limit=card.current_limit,
        projected_limit=recommended,
        dpd_max_12m=customer.dpd_max_12m,
        utilization_pct=beh.utilization_pct,
    )

    # L3a policy guardrails — only apply to UPGRADE
    if decision_type == "UPGRADE":
        pol = policy.check_upgrade_eligibility(
            config=config,
            proposed_limit=recommended,
            income_estimate=inc.estimate_inr,
            dpd_max_12m=customer.dpd_max_12m,
            months_at_current_limit=card.months_at_current_limit,
            pd_post=risk_post.pd_post_projected,
        )
        if not pol.passes:
            decision_type = "FREEZE"
            recommended = card.current_limit
            reason_codes = pol.violated_codes

    # Benefits tier coupling — the Hyperface differentiator from the brief
    tier_from = card.benefits_tier
    tier_to = tier_for_limit(recommended) if decision_type == "UPGRADE" else tier_from

    # HITL gating
    delta = abs(recommended - card.current_limit)
    hitl_required = decision_type == "UPGRADE" and policy.requires_hitl(limit_delta_inr=delta, config=config)

    # Confidence — composite of behavioral score, income confidence, inverse PD
    confidence = round(
        0.5 * (beh.score / 100) + 0.3 * inc.confidence + 0.2 * (1.0 - min(risk_post.pd_post_projected / 0.1, 1.0)),
        3,
    )

    expl = explainer.render(
        decision=decision_type,
        current_limit=card.current_limit,
        recommended_limit=recommended,
        reason_codes=reason_codes,
        behavioral_score=beh.score,
        behavior_delta_signals=beh.signals,
        income_estimate=inc.estimate_inr,
        income_delta_pct=inc.delta_vs_stated_pct,
        pd_pre=risk_pre.pd_pre,
        pd_post=risk_post.pd_post_projected,
        benefits_tier_from=tier_from,
        benefits_tier_to=tier_to,
    )

    decision_id = f"CLR-DEC-{uuid.uuid4().hex[:8].upper()}"
    dec = Decision(
        id=decision_id,
        customer_id=customer.id,
        card_id=card.id,
        created_at=datetime.utcnow(),
        current_limit=card.current_limit,
        recommended_limit=recommended,
        decision=decision_type,
        confidence=confidence,
        pd_pre=risk_pre.pd_pre,
        pd_post_projected=risk_post.pd_post_projected,
        income_estimate=inc.estimate_inr,
        behavioral_score=beh.score,
        reason_codes=reason_codes,
        explainer_text_officer=expl.officer_text,
        explainer_text_customer=expl.customer_text,
        trigger_type=trigger_type,
        hitl_required=hitl_required,
        hitl_status="PENDING" if hitl_required else "N/A",
        benefits_tier_from=tier_from,
        benefits_tier_to=tier_to if decision_type == "UPGRADE" and tier_to != tier_from else None,
        executed=False,
    )
    db.add(dec)
    db.add(AuditLog(
        entity_type="Decision",
        entity_id=decision_id,
        action="CREATED",
        payload={
            "decision": decision_type,
            "trigger_type": trigger_type,
            "behavioral_score": beh.score,
            "income_estimate": inc.estimate_inr,
            "pd_pre": risk_pre.pd_pre,
            "pd_post": risk_post.pd_post_projected,
            "reason_codes": reason_codes,
        },
    ))
    db.commit()
    db.refresh(dec)
    return dec
