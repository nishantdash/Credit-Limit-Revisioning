from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CashflowSignal, Customer, Decision, Transaction
from ..schemas import CardOut, CustomerOut

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[CustomerOut])
def list_customers(limit: int = 500, db: Session = Depends(get_db)):
    # Bound the payload so a large uploaded book doesn't make the page crawl.
    # Seeded CIF-* ids sort before uploaded ids, so the demo roster stays visible.
    return db.query(Customer).order_by(Customer.id).limit(limit).all()


@router.get("/{customer_id}")
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, "Customer not found")
    card = customer.cards[0] if customer.cards else None
    txns = (
        db.query(Transaction)
        .filter(Transaction.card_id == card.id)
        .order_by(Transaction.timestamp.desc())
        .limit(20)
        .all()
        if card else []
    )
    cashflow = db.query(CashflowSignal).filter(CashflowSignal.customer_id == customer.id).all()
    latest = (
        db.query(Decision)
        .filter(Decision.customer_id == customer.id)
        .order_by(Decision.created_at.desc())
        .first()
    )
    return {
        "customer": CustomerOut.model_validate(customer),
        "card": CardOut.model_validate(card) if card else None,
        "latest_tier": latest.risk_tier if latest else None,
        "latest_intent": latest.intent if latest else None,
        "recent_transactions": [
            {
                "id": t.id, "amount": t.amount, "category_class": t.category_class,
                "merchant_category": t.merchant_category, "merchant_quality": t.merchant_quality,
                "is_recurring": t.is_recurring, "is_declined": t.is_declined,
                "merchant_city": t.merchant_city, "timestamp": t.timestamp,
            } for t in txns
        ],
        "cashflow_signals": [
            {"source": s.source, "monthly_amount": s.monthly_amount,
             "regularity": s.regularity, "as_of": s.as_of}
            for s in cashflow
        ],
    }
