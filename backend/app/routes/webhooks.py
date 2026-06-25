"""L1/L5 — Hyperface ↔ CLR webhook contracts (per brainstorm §9).

Hyperface fires events INTO CLR (utilisation threshold, spend spike, enriched
transaction stream). CLR fires limit-upgrade instructions BACK to Hyperface
for atomic CBS + network + notification fanout.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..engine import trigger as trigger_engine
from ..engine.hitl_executor import auto_execute_if_eligible
from ..models import AuditLog, Card, Decision, Transaction
from ..schemas import WebhookEvent

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/hyperface/event")
def receive_hyperface_event(evt: WebhookEvent, db: Session = Depends(get_db)):
    """Single inbound endpoint for all Hyperface → CLR events."""
    card = db.query(Card).filter(Card.id == evt.card_id).first()
    if not card:
        raise HTTPException(404, f"Unknown card {evt.card_id}")

    db.add(AuditLog(
        entity_type="WebhookInbound",
        entity_id=evt.card_id,
        action=evt.event_type,
        actor="hyperface",
        payload=evt.model_dump(mode="json"),
    ))

    if evt.event_type == "TRANSACTION_ENRICHED":
        # Enriched stream — append a transaction row but don't run a decision.
        # Decision runs only on threshold/spike events to avoid review thrash.
        db.add(Transaction(
            id=f"TXN-WH-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
            card_id=evt.card_id,
            amount=evt.current_balance or 0,
            merchant_category="UNKNOWN",
            merchant_tier="STANDARD",
            timestamp=evt.timestamp or datetime.utcnow(),
        ))
        db.commit()
        return {"received": True, "decision_triggered": False}

    if evt.event_type in {"CARD_UTILIZATION_THRESHOLD", "SPEND_SPIKE_DETECTED", "INCOME_STEPCHANGE"}:
        if evt.current_balance is not None:
            card.current_balance = evt.current_balance
        dec = trigger_engine.fire_event(
            db,
            card_id=evt.card_id,
            event_type=evt.event_type,
            payload=evt.model_dump(mode="json"),
        )
        auto_execute_if_eligible(db, dec)
        db.commit()
        return {
            "received": True,
            "decision_triggered": True,
            "decision_id": dec.id,
            "decision": dec.decision,
            "hitl_required": dec.hitl_required,
        }

    db.commit()
    return {"received": True, "decision_triggered": False}


@router.get("/hyperface/outbound/{decision_id}")
def preview_hyperface_outbound(decision_id: str, db: Session = Depends(get_db)):
    """Returns the LIMIT_UPGRADE instruction payload that CLR would post to
    Hyperface for the atomic write-back. Mirrors the §9 contract."""
    dec = db.query(Decision).filter(Decision.id == decision_id).first()
    if not dec:
        raise HTTPException(404, "Decision not found")
    card = db.query(Card).filter(Card.id == dec.card_id).first()
    customer_segment_tier = dec.benefits_tier_to or dec.benefits_tier_from or card.benefits_tier
    return {
        "instruction_type": "LIMIT_UPGRADE" if dec.decision == "UPGRADE" else dec.decision,
        "customer_id": dec.customer_id,
        "card_id": dec.card_id,
        "programme_id": card.customer.programme_id if card.customer else None,
        "current_limit": dec.current_limit,
        "new_limit": dec.recommended_limit,
        "benefits_tier_change": {
            "from": dec.benefits_tier_from,
            "to": dec.benefits_tier_to,
        } if dec.benefits_tier_to else None,
        "notification_payload": {
            "channel": "PUSH",
            "headline": (
                "Your credit limit has been upgraded" if dec.decision == "UPGRADE"
                else "Your credit limit has been updated"
            ),
            "body": dec.explainer_text_customer,
            "cta": "View new benefits" if dec.benefits_tier_to else "View details",
            "cta_url": "https://litcard.au.com/benefits",
        },
        "audit_reference": dec.id,
        "hitl_approved_by": dec.hitl_decided_by,
        "auto_approved": not dec.hitl_required,
    }
