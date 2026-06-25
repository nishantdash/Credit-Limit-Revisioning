from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Card, Customer, IncomeSignal, Transaction
from ..schemas import CardOut, CustomerOut

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[CustomerOut])
def list_customers(db: Session = Depends(get_db)):
    return db.query(Customer).order_by(Customer.id).all()


@router.get("/{customer_id}")
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, "Customer not found")
    card = customer.cards[0] if customer.cards else None
    txns = db.query(Transaction).filter(Transaction.card_id == card.id).order_by(Transaction.timestamp.desc()).limit(20).all() if card else []
    income_signals = db.query(IncomeSignal).filter(IncomeSignal.customer_id == customer.id).all()
    return {
        "customer": CustomerOut.model_validate(customer),
        "card": CardOut.model_validate(card) if card else None,
        "recent_transactions": [
            {
                "id": t.id,
                "amount": t.amount,
                "merchant_category": t.merchant_category,
                "merchant_tier": t.merchant_tier,
                "merchant_city": t.merchant_city,
                "timestamp": t.timestamp,
            } for t in txns
        ],
        "income_signals": [
            {"source": s.source, "monthly_amount": s.monthly_amount, "as_of": s.as_of}
            for s in income_signals
        ],
    }
