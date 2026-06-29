"""Trigger engine (§7.2).

  - Event-driven:   salary credit, large pre-auth, declined high-value txn,
                    utilisation threshold, missed obligation via AA
  - Threshold-driven: utilisation / min-due-dependency slope crosses a band
  - Scheduled micro-reviews: lightweight continuous re-scoring (replaces the
                    quarterly batch)

Each trigger writes a TriggerEvent, runs the decision engine, and hands the
result to the consent-asymmetric orchestrator.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from ..models import Card, Customer, Decision, TriggerEvent
from . import config as cfg_mod
from . import decision as decision_engine
from . import orchestration


def fire_event(db: Session, *, card_id: str, event_type: str,
               payload: Optional[dict[str, Any]] = None,
               config: Optional[cfg_mod.TenantConfig] = None) -> Decision:
    config = config or cfg_mod.load_active(db)
    card: Card = db.query(Card).filter(Card.id == card_id).one()
    evt = TriggerEvent(card_id=card_id, event_type=event_type, payload=payload or {},
                       timestamp=datetime.utcnow())
    db.add(evt)
    db.flush()
    dec = decision_engine.decide(db, customer_id=card.customer_id,
                                 trigger_type=event_type, config=config)
    evt.decision_id = dec.id
    orchestration.auto_orchestrate(db, dec)
    db.commit()
    db.refresh(dec)
    return dec


def micro_review_sweep(db: Session, config: Optional[cfg_mod.TenantConfig] = None) -> list[Decision]:
    """Continuous micro-review across the book — replaces the quarterly batch."""
    config = config or cfg_mod.load_active(db)
    decisions: list[Decision] = []
    for customer in db.query(Customer).all():
        if not customer.cards:
            continue
        card = customer.cards[0]
        evt = TriggerEvent(card_id=card.id, event_type="MICRO_REVIEW_SWEEP",
                           payload={"sweep_at": datetime.utcnow().isoformat()})
        db.add(evt)
        db.flush()
        dec = decision_engine.decide(db, customer_id=customer.id,
                                     trigger_type="MICRO_REVIEW_SWEEP", config=config)
        evt.decision_id = dec.id
        orchestration.auto_orchestrate(db, dec)
        decisions.append(dec)
    db.commit()
    return decisions
