"""Offer pipeline (§6.1) — consent-gated limit increases.

Increases are computed and *offered* but stay paused until the customer actively
approves via OTP/MPIN. Silence is never approval.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..engine import orchestration
from ..models import Card, Decision
from ..schemas import ConsentAction, DecisionOut

router = APIRouter(prefix="/offers", tags=["offers"])


@router.get("", response_model=list[DecisionOut])
def list_offers(status: str = "PENDING_CONSENT", db: Session = Depends(get_db)):
    q = db.query(Decision).filter(Decision.pipeline == "OFFER")
    if status and status.upper() != "ALL":
        q = q.filter(Decision.consent_status == status.upper())
    # Only surface offers that have actually been dispatched (not held for review).
    q = q.filter(Decision.review_status != "PENDING")
    return q.order_by(Decision.created_at.desc()).all()


@router.post("/{decision_id}/consent", response_model=DecisionOut)
def give_consent(decision_id: str, action: ConsentAction, db: Session = Depends(get_db)):
    dec = db.query(Decision).filter(Decision.id == decision_id).first()
    if not dec:
        raise HTTPException(404, "Offer not found")
    if dec.pipeline != "OFFER":
        raise HTTPException(400, "Decision is not an offer")
    if dec.consent_status != "PENDING_CONSENT":
        raise HTTPException(400, f"Offer is {dec.consent_status}, not awaiting consent")
    if dec.review_status == "PENDING":
        raise HTTPException(400, "Offer is held for officer review before dispatch")
    orchestration.accept_offer(db, dec, actor=action.actor, channel=action.channel)
    db.commit()
    db.refresh(dec)
    return dec


@router.post("/{decision_id}/decline", response_model=DecisionOut)
def decline(decision_id: str, action: ConsentAction, db: Session = Depends(get_db)):
    dec = db.query(Decision).filter(Decision.id == decision_id).first()
    if not dec:
        raise HTTPException(404, "Offer not found")
    if dec.pipeline != "OFFER":
        raise HTTPException(400, "Decision is not an offer")
    if dec.consent_status != "PENDING_CONSENT":
        raise HTTPException(400, f"Offer is {dec.consent_status}")
    orchestration.decline_offer(db, dec, actor=action.actor)
    db.commit()
    db.refresh(dec)
    return dec
