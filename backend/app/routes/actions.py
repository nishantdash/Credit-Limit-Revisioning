"""Action pipeline (§6.1) — risk-driven decreases applied proactively.

RBI permits risk decreases without pre-approval, so these are applied with an
operational buffer above outstanding and the customer is notified. This route is
read-only; application happens automatically in the orchestrator (or on review
approval for low-confidence cuts).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Decision
from ..schemas import DecisionOut

router = APIRouter(prefix="/actions", tags=["actions"])


@router.get("", response_model=list[DecisionOut])
def list_actions(db: Session = Depends(get_db)):
    return (
        db.query(Decision)
        .filter(Decision.pipeline == "ACTION")
        .order_by(Decision.created_at.desc())
        .all()
    )
