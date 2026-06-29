"""Consent-asymmetric orchestration (§6.1).

Increases are an OFFER pipeline; decreases are an ACTION pipeline. The entire
write-back layer is built on this split:

  ACTION (decrease) — RBI permits risk-driven decreases proactively, so the
      engine applies the new limit (with operational buffer) and notifies. No
      pre-approval. Low-confidence decreases are held for manual review first.
  OFFER  (increase) — RBI requires explicit consent; the engine computes and
      *offers*, but the limit stays paused until the customer approves via
      OTP/MPIN. Never auto-applied. Low-confidence offers wait for officer review
      before dispatch.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from ..models import AuditLog, Card, Decision


def _apply_limit(db: Session, dec: Decision, *, actor: str, action: str) -> None:
    card: Card = db.query(Card).filter(Card.id == dec.card_id).one()
    prev = card.current_limit
    card.current_limit = dec.recommended_limit
    card.months_since_last_change = 0
    if dec.direction == "DECREASE":
        card.months_inactive = 0
    dec.executed = True
    dec.executed_at = datetime.utcnow()
    dec.customer_notified = True
    db.add(AuditLog(
        entity_type="Card", entity_id=card.id, action=action, actor=actor,
        payload={"from_limit": prev, "to_limit": dec.recommended_limit,
                 "decision_id": dec.id, "direction": dec.direction,
                 "duration": dec.duration, "pipeline": dec.pipeline},
    ))


def auto_orchestrate(db: Session, dec: Decision) -> None:
    """Run immediately after a decision is produced.

    ACTION decreases auto-apply (unless flagged for review). OFFER increases are
    dispatched as consent-gated offers and stay paused. MAINTAIN/FREEZE no-op.
    """
    if dec.review_required:
        return  # held for human review before any execution / dispatch
    if dec.pipeline == "ACTION":
        _apply_limit(db, dec, actor="clr_engine", action="LIMIT_DECREASED_AUTO")
    elif dec.pipeline == "OFFER":
        # Offer is now live and awaiting customer OTP/MPIN — nothing applied.
        dec.customer_notified = True
        db.add(AuditLog(
            entity_type="Offer", entity_id=dec.id, action="OFFER_DISPATCHED", actor="clr_engine",
            payload={"customer_id": dec.customer_id, "new_limit": dec.recommended_limit,
                     "channel": dec.consent_channel},
        ))


def accept_offer(db: Session, dec: Decision, *, actor: str, channel: str | None = None) -> None:
    dec.consent_status = "ACCEPTED"
    dec.consent_channel = channel or dec.consent_channel
    dec.consent_decided_at = datetime.utcnow()
    db.add(AuditLog(
        entity_type="Offer", entity_id=dec.id, action="CONSENT_ACCEPTED", actor=actor,
        payload={"channel": dec.consent_channel},
    ))
    _apply_limit(db, dec, actor=actor, action="LIMIT_INCREASED_ON_CONSENT")


def decline_offer(db: Session, dec: Decision, *, actor: str) -> None:
    dec.consent_status = "DECLINED"
    dec.consent_decided_at = datetime.utcnow()
    db.add(AuditLog(
        entity_type="Offer", entity_id=dec.id, action="CONSENT_DECLINED", actor=actor, payload={},
    ))
