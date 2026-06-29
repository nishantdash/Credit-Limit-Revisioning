"""Analytics (§7.3, §10) — portfolio funnel, ROI, and the anti-spiral guardrail
status that keeps the engine honest."""
from collections import Counter
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..engine import config as cfg_mod
from ..models import AuditLog, Card, Customer, Decision, TriggerEvent
from ..schemas import FunnelMetrics, GuardrailStatus, RoiMetrics

router = APIRouter(prefix="/analytics", tags=["analytics"])

INTERCHANGE_TAKE_PCT = 0.012   # ~120 bps Indian credit-card interchange
SPEND_TO_LIMIT_RATIO = 0.40    # incremental spend assumed at 40% of activated uplift


@router.get("/funnel", response_model=FunnelMetrics)
def funnel(db: Session = Depends(get_db)):
    decisions = db.query(Decision).all()
    by_intent = Counter(d.intent for d in decisions)
    by_tier = Counter(f"tier{d.risk_tier}" for d in decisions)
    by_direction = Counter(d.direction for d in decisions)
    return FunnelMetrics(
        customers=db.query(Customer).count(),
        reviewed=len(decisions),
        by_intent=dict(by_intent),
        by_tier=dict(by_tier),
        by_direction=dict(by_direction),
        offers_pending_consent=sum(1 for d in decisions if d.pipeline == "OFFER" and d.consent_status == "PENDING_CONSENT" and d.review_status != "PENDING"),
        offers_accepted=sum(1 for d in decisions if d.consent_status == "ACCEPTED"),
        actions_applied=sum(1 for d in decisions if d.pipeline == "ACTION" and d.executed),
        review_pending=sum(1 for d in decisions if d.review_status == "PENDING"),
        knockouts=sum(1 for d in decisions if d.intent == "KNOCKOUT"),
    )


@router.get("/roi", response_model=RoiMetrics)
def roi(db: Session = Depends(get_db)):
    decisions = db.query(Decision).all()
    if not decisions:
        return RoiMetrics(offered_uplift_inr=0, activated_uplift_inr=0, exposure_reduced_inr=0,
                          avg_pd_pre=0, avg_pd_post=0, increases=0, decreases=0,
                          temporary_offers=0, estimated_incremental_interchange_monthly_inr=0)
    increases = [d for d in decisions if d.direction == "INCREASE"]
    decreases = [d for d in decisions if d.direction == "DECREASE"]
    offered = sum(d.recommended_limit - d.current_limit for d in increases)
    activated = sum(d.recommended_limit - d.current_limit for d in increases if d.consent_status == "ACCEPTED")
    exposure_cut = sum(d.current_limit - d.recommended_limit for d in decreases if d.executed)
    est_interchange = activated * SPEND_TO_LIMIT_RATIO * INTERCHANGE_TAKE_PCT
    return RoiMetrics(
        offered_uplift_inr=round(offered, 0),
        activated_uplift_inr=round(activated, 0),
        exposure_reduced_inr=round(exposure_cut, 0),
        avg_pd_pre=round(sum(d.pd_pre for d in decisions) / len(decisions), 4),
        avg_pd_post=round(sum(d.pd_post_projected for d in decisions) / len(decisions), 4),
        increases=len(increases),
        decreases=len(decreases),
        temporary_offers=sum(1 for d in increases if d.duration == "TEMPORARY"),
        estimated_incremental_interchange_monthly_inr=round(est_interchange, 0),
    )


@router.get("/guardrails", response_model=GuardrailStatus)
def guardrails(db: Session = Depends(get_db)):
    config = cfg_mod.load_active(db)
    total_limit = sum(c.current_limit for c in db.query(Card).all()) or 1.0
    since = datetime.utcnow() - timedelta(days=30)
    recent_increases = (
        db.query(Decision)
        .filter(Decision.created_at >= since, Decision.direction == "INCREASE")
        .all()
    )
    extended = sum(
        (d.recommended_limit - d.current_limit)
        for d in recent_increases
        if d.executed or d.consent_status == "ACCEPTED"
    )
    used_pct = extended / total_limit
    cap_pct = config.portfolio_increase_velocity_cap_pct

    cap_counter: Counter = Counter()
    capped = 0
    for d in db.query(Decision).all():
        if d.applied_caps:
            capped += 1
            for c in d.applied_caps:
                cap_counter[c] += 1

    return GuardrailStatus(
        portfolio_increase_cap_pct=round(cap_pct * 100, 2),
        portfolio_increase_used_pct=round(used_pct * 100, 2),
        portfolio_headroom_pct=round(max(0.0, cap_pct - used_pct) * 100, 2),
        total_book_limit_inr=round(total_limit, 0),
        increase_extended_30d_inr=round(extended, 0),
        decisions_capped=capped,
        cap_breakdown=dict(cap_counter),
    )


@router.get("/audit-log")
def audit_log(db: Session = Depends(get_db), limit: int = 200):
    rows = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [
        {"timestamp": r.timestamp, "entity_type": r.entity_type, "entity_id": r.entity_id,
         "action": r.action, "actor": r.actor, "payload": r.payload}
        for r in rows
    ]


@router.get("/trigger-events")
def trigger_events(db: Session = Depends(get_db), limit: int = 100):
    rows = db.query(TriggerEvent).order_by(TriggerEvent.timestamp.desc()).limit(limit).all()
    return [
        {"id": r.id, "card_id": r.card_id, "event_type": r.event_type,
         "timestamp": r.timestamp, "decision_id": r.decision_id, "payload": r.payload}
        for r in rows
    ]
