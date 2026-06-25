"""L7 — Bank-facing analytics. Funnel, ROI, A/B-style cohort placeholder."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AuditLog, Card, Customer, Decision, TriggerEvent
from ..schemas import FunnelMetrics, RoiMetrics

router = APIRouter(prefix="/analytics", tags=["analytics"])

INTERCHANGE_TAKE_PCT = 0.012   # ~120 bps; rough Indian credit card interchange average
SPEND_TO_LIMIT_RATIO = 0.4     # spend uplift assumed at 40% of incremental limit


@router.get("/funnel", response_model=FunnelMetrics)
def funnel(db: Session = Depends(get_db)):
    eligible = db.query(Customer).count()
    reviewed = db.query(Decision).count()
    upgrade = db.query(Decision).filter(Decision.decision == "UPGRADE").count()
    downgrade = db.query(Decision).filter(Decision.decision == "DOWNGRADE").count()
    freeze = db.query(Decision).filter(Decision.decision == "FREEZE").count()
    hitl_pending = db.query(Decision).filter(
        Decision.hitl_required.is_(True), Decision.hitl_status == "PENDING"
    ).count()
    executed = db.query(Decision).filter(Decision.executed.is_(True)).count()
    notified = db.query(Decision).filter(Decision.customer_notified.is_(True)).count()
    accepted = db.query(Decision).filter(Decision.customer_accepted.is_(True)).count()
    return FunnelMetrics(
        eligible=eligible,
        reviewed=reviewed,
        upgrade_recommended=upgrade,
        downgrade_recommended=downgrade,
        freeze_recommended=freeze,
        hitl_pending=hitl_pending,
        executed=executed,
        customer_notified=notified,
        customer_accepted=accepted,
    )


@router.get("/roi", response_model=RoiMetrics)
def roi(db: Session = Depends(get_db)):
    decisions = db.query(Decision).all()
    if not decisions:
        return RoiMetrics(
            total_limit_uplift_inr=0,
            avg_pd_pre=0,
            avg_pd_post=0,
            upgrades_count=0,
            downgrades_count=0,
            benefits_tier_upgrades=0,
            estimated_incremental_interchange_monthly_inr=0,
        )
    uplift = sum(
        (d.recommended_limit - d.current_limit) for d in decisions
        if d.decision == "UPGRADE" and d.executed
    )
    upgrades = [d for d in decisions if d.decision == "UPGRADE"]
    downgrades = [d for d in decisions if d.decision == "DOWNGRADE"]
    tier_ups = [d for d in decisions if d.benefits_tier_to and d.benefits_tier_to != d.benefits_tier_from]
    estimated_spend_uplift = uplift * SPEND_TO_LIMIT_RATIO
    estimated_interchange = estimated_spend_uplift * INTERCHANGE_TAKE_PCT
    return RoiMetrics(
        total_limit_uplift_inr=round(uplift, 2),
        avg_pd_pre=round(sum(d.pd_pre for d in decisions) / len(decisions), 4),
        avg_pd_post=round(sum(d.pd_post_projected for d in decisions) / len(decisions), 4),
        upgrades_count=len(upgrades),
        downgrades_count=len(downgrades),
        benefits_tier_upgrades=len(tier_ups),
        estimated_incremental_interchange_monthly_inr=round(estimated_interchange, 2),
    )


@router.get("/audit-log")
def audit_log(db: Session = Depends(get_db), limit: int = 100):
    rows = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [
        {
            "timestamp": r.timestamp,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "action": r.action,
            "actor": r.actor,
            "payload": r.payload,
        } for r in rows
    ]


@router.get("/trigger-events")
def trigger_events(db: Session = Depends(get_db), limit: int = 100):
    rows = db.query(TriggerEvent).order_by(TriggerEvent.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "card_id": r.card_id,
            "event_type": r.event_type,
            "timestamp": r.timestamp,
            "decision_id": r.decision_id,
            "payload": r.payload,
        } for r in rows
    ]
