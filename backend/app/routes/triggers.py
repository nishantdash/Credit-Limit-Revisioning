from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from sqlalchemy.orm import Session

from ..db import get_db
from ..engine import trigger as trigger_engine
from ..engine.hitl_executor import auto_execute_if_eligible
from ..models import Card, AuditLog
from ..schemas import DecisionOut, TriggerRequest

router = APIRouter(prefix="/triggers", tags=["triggers"])


@router.post("/fire", response_model=DecisionOut)
def fire_trigger(req: TriggerRequest, db: Session = Depends(get_db)):
    card = db.query(Card).filter(Card.id == req.card_id).first()
    if not card:
        raise HTTPException(404, "Card not found")
    dec = trigger_engine.fire_event(
        db,
        card_id=req.card_id,
        event_type=req.event_type,
        payload=req.payload,
    )
    # Auto-execute non-HITL decisions immediately (simulates the §5 atomic write-back).
    auto_execute_if_eligible(db, dec)
    db.commit()
    db.refresh(dec)
    return dec


@router.post("/periodic-sweep", response_model=list[DecisionOut])
def run_sweep(db: Session = Depends(get_db)):
    decisions = trigger_engine.periodic_sweep(db)
    for dec in decisions:
        auto_execute_if_eligible(db, dec)
    db.commit()
    return decisions
