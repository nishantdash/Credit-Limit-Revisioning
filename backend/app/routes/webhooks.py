"""Account Aggregator (AA) data rail + event ingress (§6.3, §7.2).

The engine consumes consent-based, ReBIT-standardised data via the AA framework
(the lender is a registered FIU). Inbound events — salary credit, payment clear,
declined high-value transaction, AA data push, or a consent revocation — update
state and (for material events) fire a decision through the consent-asymmetric
orchestrator.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..engine import trigger as trigger_engine
from ..models import AuditLog, Card, Customer
from ..schemas import WebhookEvent

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

DECISION_EVENTS = {
    "SALARY_CREDIT", "PAYMENT_CLEARED", "DECLINED_HIGH_VALUE_TXN",
    "UTILIZATION_THRESHOLD", "MIN_DUE_DEPENDENCY_SLOPE", "AA_DATA_PUSH",
    "MISSED_OBLIGATION",
}


@router.post("/aa/event")
def receive_aa_event(evt: WebhookEvent, db: Session = Depends(get_db)):
    card = db.query(Card).filter(Card.id == evt.card_id).first()
    if not card:
        raise HTTPException(404, f"Unknown card {evt.card_id}")

    db.add(AuditLog(entity_type="WebhookInbound", entity_id=evt.card_id, action=evt.event_type,
                    actor="account_aggregator", payload=evt.model_dump(mode="json")))

    # Update mutable card state from the event payload.
    if evt.outstanding is not None:
        card.outstanding = evt.outstanding
    if evt.statement_balance is not None:
        card.statement_balance = evt.statement_balance
    if evt.last_payment is not None:
        card.last_payment = evt.last_payment
    if evt.min_due_last is not None:
        card.min_due_last = evt.min_due_last

    # Consent revocation degrades the engine gracefully to internal-only signals.
    if evt.event_type == "AA_CONSENT_REVOKED" or evt.aa_consent_active is False:
        customer = db.query(Customer).filter(Customer.id == card.customer_id).first()
        if customer:
            customer.aa_consent_active = False
        db.commit()
        return {"received": True, "decision_triggered": False, "aa_consent_active": False}

    if evt.event_type in DECISION_EVENTS:
        dec = trigger_engine.fire_event(db, card_id=evt.card_id, event_type=evt.event_type,
                                        payload=evt.model_dump(mode="json"))
        return {
            "received": True, "decision_triggered": True, "decision_id": dec.id,
            "intent": dec.intent, "direction": dec.direction, "pipeline": dec.pipeline,
            "review_required": dec.review_required,
        }

    db.commit()
    return {"received": True, "decision_triggered": False}


@router.get("/cbs/outbound/{decision_id}")
def cbs_outbound(decision_id: str, db: Session = Depends(get_db)):
    """The instruction payload the engine writes to the core banking system —
    an OFFER (paused, consent-gated) or an applied ACTION."""
    from ..models import Decision

    dec = db.query(Decision).filter(Decision.id == decision_id).first()
    if not dec:
        raise HTTPException(404, "Decision not found")
    if dec.pipeline == "OFFER":
        instruction = "LIMIT_INCREASE_OFFER"
        applied = False
        headline = "You're eligible for a higher credit limit"
    elif dec.pipeline == "ACTION":
        instruction = "LIMIT_DECREASE_APPLIED"
        applied = dec.executed
        headline = "Your credit limit has been updated"
    else:
        instruction = "NO_CHANGE"
        applied = False
        headline = "Your credit limit is unchanged"
    return {
        "instruction_type": instruction,
        "customer_id": dec.customer_id,
        "card_id": dec.card_id,
        "current_limit": dec.current_limit,
        "new_limit": dec.recommended_limit,
        "direction": dec.direction,
        "duration": dec.duration,
        "auto_revert_at": dec.auto_revert_at,
        "consent_required": dec.pipeline == "OFFER",
        "consent_channel": dec.consent_channel,
        "applied": applied,
        "notification": {
            "channel": "PUSH",
            "headline": headline,
            "body": dec.consent_copy or dec.explainer_customer,
            "cta": "Approve limit" if dec.pipeline == "OFFER" else "View details",
        },
        "reason_codes": dec.reason_codes,
        "audit_reference": dec.id,
    }
