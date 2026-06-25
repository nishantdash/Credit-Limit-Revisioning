"""Helper that performs the L5 atomic write-back for decisions that don't
require HITL approval. Mirrors the §5 'CLR → Hyperface → CBS + network +
notification' flow as a single transactional update on the Card row.
"""
from datetime import datetime
from sqlalchemy.orm import Session

from ..models import AuditLog, Card, Decision


def auto_execute_if_eligible(db: Session, dec: Decision) -> None:
    if dec.hitl_required:
        return
    if dec.executed:
        return
    if dec.decision == "FREEZE":
        # Still mark notified — we may notify "no change" or simply close the loop silently.
        dec.executed = True
        dec.executed_at = datetime.utcnow()
        dec.customer_notified = False
        return

    card: Card = db.query(Card).filter(Card.id == dec.card_id).one()
    prev_limit = card.current_limit
    prev_tier = card.benefits_tier
    card.current_limit = dec.recommended_limit
    if dec.benefits_tier_to:
        card.benefits_tier = dec.benefits_tier_to
    card.months_at_current_limit = 0
    dec.executed = True
    dec.executed_at = datetime.utcnow()
    dec.customer_notified = True
    db.add(AuditLog(
        entity_type="Card",
        entity_id=card.id,
        action="LIMIT_UPDATED_AUTO",
        actor="clr_engine",
        payload={
            "from_limit": prev_limit,
            "to_limit": dec.recommended_limit,
            "benefits_tier_from": prev_tier,
            "benefits_tier_to": dec.benefits_tier_to,
            "decision_id": dec.id,
        },
    ))
