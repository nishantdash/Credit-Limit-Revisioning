from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..engine import trigger as trigger_engine
from ..models import Card
from ..schemas import DecisionOut, TriggerRequest

router = APIRouter(prefix="/triggers", tags=["triggers"])


@router.post("/fire", response_model=DecisionOut)
def fire_trigger(req: TriggerRequest, db: Session = Depends(get_db)):
    card = db.query(Card).filter(Card.id == req.card_id).first()
    if not card:
        raise HTTPException(404, "Card not found")
    return trigger_engine.fire_event(
        db, card_id=req.card_id, event_type=req.event_type, payload=req.payload,
    )


@router.post("/micro-review-sweep", response_model=list[DecisionOut])
def micro_review_sweep(db: Session = Depends(get_db)):
    return trigger_engine.micro_review_sweep(db)
