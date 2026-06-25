"""L3c — Trigger engine.

Three modes from the brief:
  - Event-driven (utilisation threshold, spend spike, missed payment)
  - Periodic sweep (monthly batch over the eligible pool)
  - Real-time income (income estimator detects a step-change)

Each trigger writes a TriggerEvent and dispatches to the decision engine.
"""
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from ..models import Card, Customer, Decision, TriggerEvent
from . import decision as decision_engine


def fire_event(
    db: Session,
    *,
    card_id: str,
    event_type: str,
    payload: Optional[dict[str, Any]] = None,
) -> Decision:
    card: Card = db.query(Card).filter(Card.id == card_id).one()
    evt = TriggerEvent(
        card_id=card_id,
        event_type=event_type,
        payload=payload or {},
        timestamp=datetime.utcnow(),
    )
    db.add(evt)
    db.flush()

    dec = decision_engine.decide(
        db,
        customer_id=card.customer_id,
        trigger_type=event_type,
    )
    evt.decision_id = dec.id
    db.commit()
    return dec


def periodic_sweep(db: Session) -> list[Decision]:
    """Run a sweep over every eligible customer — equivalent of the monthly batch."""
    decisions: list[Decision] = []
    for customer in db.query(Customer).all():
        if not customer.cards:
            continue
        card = customer.cards[0]
        evt = TriggerEvent(
            card_id=card.id,
            event_type="PERIODIC_SWEEP",
            payload={"sweep_at": datetime.utcnow().isoformat()},
        )
        db.add(evt)
        db.flush()
        dec = decision_engine.decide(db, customer_id=customer.id, trigger_type="PERIODIC_SWEEP")
        evt.decision_id = dec.id
        decisions.append(dec)
    db.commit()
    return decisions
