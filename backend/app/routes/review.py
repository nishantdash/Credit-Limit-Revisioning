"""Manual review queue (§3.3, §11) — confidence-gated human-in-the-loop.

Low-confidence decisions don't auto-apply. Increases are held *before* the offer
is dispatched; sharp low-confidence decreases are held *before* application. An
officer approves (releasing the offer / applying the cut) or rejects.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..engine import orchestration
from ..models import AuditLog, Decision
from ..schemas import DecisionOut, ReviewAction

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/queue", response_model=list[DecisionOut])
def queue(db: Session = Depends(get_db)):
    return (
        db.query(Decision)
        .filter(Decision.review_required.is_(True), Decision.review_status == "PENDING")
        .order_by(Decision.created_at.asc())
        .all()
    )


@router.post("/{decision_id}/approve", response_model=DecisionOut)
def approve(decision_id: str, action: ReviewAction, db: Session = Depends(get_db)):
    dec = _pending(db, decision_id)
    dec.review_status = "APPROVED"
    dec.review_by = action.actor
    dec.review_at = datetime.utcnow()
    dec.review_notes = action.notes
    # Release into the appropriate pipeline.
    if dec.pipeline == "ACTION":
        orchestration._apply_limit(db, dec, actor=action.actor, action="LIMIT_DECREASED_ON_REVIEW")
    elif dec.pipeline == "OFFER":
        dec.customer_notified = True
        db.add(AuditLog(entity_type="Offer", entity_id=dec.id, action="OFFER_DISPATCHED_ON_REVIEW",
                        actor=action.actor, payload={"new_limit": dec.recommended_limit}))
    db.add(AuditLog(entity_type="Decision", entity_id=dec.id, action="REVIEW_APPROVED",
                    actor=action.actor, payload={"notes": action.notes}))
    db.commit()
    db.refresh(dec)
    return dec


@router.post("/{decision_id}/reject", response_model=DecisionOut)
def reject(decision_id: str, action: ReviewAction, db: Session = Depends(get_db)):
    dec = _pending(db, decision_id)
    dec.review_status = "REJECTED"
    dec.review_by = action.actor
    dec.review_at = datetime.utcnow()
    dec.review_notes = action.notes
    if dec.pipeline == "OFFER":
        dec.consent_status = "DECLINED"
    db.add(AuditLog(entity_type="Decision", entity_id=dec.id, action="REVIEW_REJECTED",
                    actor=action.actor, payload={"notes": action.notes}))
    db.commit()
    db.refresh(dec)
    return dec


def _pending(db: Session, decision_id: str) -> Decision:
    dec = db.query(Decision).filter(Decision.id == decision_id).first()
    if not dec:
        raise HTTPException(404, "Decision not found")
    if dec.review_status != "PENDING":
        raise HTTPException(400, "Decision is not pending review")
    return dec
