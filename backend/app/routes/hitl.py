"""L3d — Human-in-the-loop maker-checker queue."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AuditLog, Card, Decision
from ..schemas import DecisionOut, HitlAction

router = APIRouter(prefix="/hitl", tags=["hitl"])


@router.get("/queue", response_model=list[DecisionOut])
def hitl_queue(db: Session = Depends(get_db)):
    return (
        db.query(Decision)
        .filter(Decision.hitl_required.is_(True), Decision.hitl_status == "PENDING")
        .order_by(Decision.created_at.asc())
        .all()
    )


@router.post("/{decision_id}/approve", response_model=DecisionOut)
def approve(decision_id: str, action: HitlAction, db: Session = Depends(get_db)):
    dec = db.query(Decision).filter(Decision.id == decision_id).first()
    if not dec:
        raise HTTPException(404, "Decision not found")
    if dec.hitl_status != "PENDING":
        raise HTTPException(400, "Decision is not pending review")
    dec.hitl_status = "APPROVED"
    dec.hitl_decided_by = action.actor
    dec.hitl_decided_at = datetime.utcnow()
    dec.hitl_notes = action.notes
    _execute_decision(db, dec, actor=action.actor)
    db.add(AuditLog(
        entity_type="Decision",
        entity_id=decision_id,
        action="HITL_APPROVED",
        actor=action.actor,
        payload={"notes": action.notes},
    ))
    db.commit()
    db.refresh(dec)
    return dec


@router.post("/{decision_id}/reject", response_model=DecisionOut)
def reject(decision_id: str, action: HitlAction, db: Session = Depends(get_db)):
    dec = db.query(Decision).filter(Decision.id == decision_id).first()
    if not dec:
        raise HTTPException(404, "Decision not found")
    if dec.hitl_status != "PENDING":
        raise HTTPException(400, "Decision is not pending review")
    dec.hitl_status = "REJECTED"
    dec.hitl_decided_by = action.actor
    dec.hitl_decided_at = datetime.utcnow()
    dec.hitl_notes = action.notes
    db.add(AuditLog(
        entity_type="Decision",
        entity_id=decision_id,
        action="HITL_REJECTED",
        actor=action.actor,
        payload={"notes": action.notes},
    ))
    db.commit()
    db.refresh(dec)
    return dec


def _execute_decision(db: Session, dec: Decision, actor: str):
    """L5 write-back — applies the limit + benefits tier change on the card row,
    simulating the atomic CBS + card-network + notification fanout from §9."""
    card: Card = db.query(Card).filter(Card.id == dec.card_id).one()
    card.current_limit = dec.recommended_limit
    if dec.benefits_tier_to:
        card.benefits_tier = dec.benefits_tier_to
    card.months_at_current_limit = 0
    dec.executed = True
    dec.executed_at = datetime.utcnow()
    dec.customer_notified = True
    db.add(AuditLog(
        entity_type="Card",
        entity_id=card.id,
        action="LIMIT_UPDATED",
        actor=actor,
        payload={
            "from_limit": dec.current_limit,
            "to_limit": dec.recommended_limit,
            "benefits_tier_from": dec.benefits_tier_from,
            "benefits_tier_to": dec.benefits_tier_to,
        },
    ))
