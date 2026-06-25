from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Decision
from ..schemas import DecisionOut

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.get("", response_model=list[DecisionOut])
def list_decisions(
    db: Session = Depends(get_db),
    decision: str | None = Query(default=None),
    limit: int = 100,
):
    q = db.query(Decision).order_by(Decision.created_at.desc())
    if decision:
        q = q.filter(Decision.decision == decision.upper())
    return q.limit(limit).all()


@router.get("/{decision_id}", response_model=DecisionOut)
def get_decision(decision_id: str, db: Session = Depends(get_db)):
    dec = db.query(Decision).filter(Decision.id == decision_id).first()
    if not dec:
        raise HTTPException(404, "Decision not found")
    return dec


@router.get("/by-customer/{customer_id}", response_model=list[DecisionOut])
def list_for_customer(customer_id: str, db: Session = Depends(get_db)):
    return (
        db.query(Decision)
        .filter(Decision.customer_id == customer_id)
        .order_by(Decision.created_at.desc())
        .all()
    )
