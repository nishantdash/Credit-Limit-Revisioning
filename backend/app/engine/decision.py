"""End-to-end decision orchestration (§7.1 logical flow).

    knockout → signals → risk/tier → intent → matrix → formulas → guardrails
            → confidence gating → consent-asymmetric pipeline split → write Decision

Increases become an OFFER pipeline (consent-gated, paused until OTP/MPIN);
decreases become an ACTION pipeline (applied with buffer + notify). The decision
emitted is the four-part object: direction, magnitude, duration, confidence.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..models import AuditLog, Card, CashflowSignal, Customer, Decision, Transaction
from . import config as cfg_mod
from . import (
    explainer,
    guardrails,
    intent as intent_mod,
    knockout,
    matrix as matrix_mod,
    msme,
    risk as risk_mod,
    signals as signals_mod,
)

SEASONAL_REVERT_DAYS = 60


def _round_to(value: float, step: float) -> float:
    return round(value / step) * step if step else value


def _leverage_context(db: Session, customer: Customer, card: Card,
                      config: cfg_mod.TenantConfig) -> guardrails.GuardrailContext:
    now = datetime.utcnow()
    window_start = now - timedelta(days=config.leverage_window_months * 30)
    prior = (
        db.query(Decision)
        .filter(Decision.customer_id == customer.id, Decision.created_at >= window_start)
        .all()
    )
    cumulative = sum(
        (d.magnitude_pct / 100.0)
        for d in prior
        if d.direction == "INCREASE" and (d.executed or d.consent_status == "ACCEPTED")
    )
    last = (
        db.query(Decision)
        .filter(Decision.customer_id == customer.id)
        .order_by(Decision.created_at.desc())
        .first()
    )
    recently_decreased = bool(last and last.direction == "DECREASE" and last.executed)

    # Portfolio increase-velocity: book uplift extended in the trailing 30 days as a
    # fraction of the total book limit (the system-level anti-spiral cap).
    book = db.query(Card).all()
    total_limit = sum(c.current_limit for c in book) or 1.0
    recent = (
        db.query(Decision)
        .filter(Decision.created_at >= now - timedelta(days=30), Decision.direction == "INCREASE")
        .all()
    )
    extended = sum(
        (d.recommended_limit - d.current_limit)
        for d in recent
        if d.executed or d.consent_status == "ACCEPTED"
    )
    portfolio_used = extended / total_limit

    return guardrails.GuardrailContext(
        months_since_last_change=card.months_since_last_change or 0,
        recently_decreased=recently_decreased,
        customer_cumulative_increase_frac=cumulative,
        portfolio_increase_used_frac=portfolio_used,
        portfolio_increase_cap_frac=config.portfolio_increase_velocity_cap_pct,
    )


def decide(db: Session, *, customer_id: str, trigger_type: str,
           config: cfg_mod.TenantConfig) -> Decision:
    customer: Customer = db.query(Customer).filter(Customer.id == customer_id).one()
    card: Card = customer.cards[0]
    txns = db.query(Transaction).filter(Transaction.card_id == card.id).all()
    cashflow = db.query(CashflowSignal).filter(CashflowSignal.customer_id == customer.id).all()

    sig = signals_mod.compute(customer, card, txns, cashflow, config)
    reason_codes: list[str] = []
    applied_caps: list[str] = []
    msme_out = None

    # ── Hard-knockout layer (evaluated first, bypasses scoring) ──────────────
    ko = knockout.evaluate(customer)
    if ko.hit:
        tier = 4
        intent = "KNOCKOUT"
        intent_conf = 1.0
        md = matrix_mod.MatrixDecision(
            direction=matrix_mod.DECREASE if customer.dpd_max_12m >= 30 else matrix_mod.FREEZE,
            duration=matrix_mod.NA, cell="Tier 4 · Hard knockout",
            note="Binary block — bypasses the intent model",
        )
        reason_codes = list(ko.triggered)
        risk_out = risk_mod.score(bureau_score=customer.bureau_score, sig=sig,
                                  current_limit=card.current_limit,
                                  projected_limit=card.current_limit, config=config)
        pd_pre = max(risk_out.pd_pre, config.tier_pd_bands["tier3"] + 0.001)
    else:
        risk_out = risk_mod.score(bureau_score=customer.bureau_score, sig=sig,
                                  current_limit=card.current_limit,
                                  projected_limit=card.current_limit, config=config)
        tier = risk_out.tier
        pd_pre = risk_out.pd_pre

        intent_res = intent_mod.classify(sig, config)
        intent = intent_res.intent
        intent_conf = intent_res.confidence
        reason_codes = list(intent_res.drivers)

        # MSME double-gate may override intent to DISTRESS via trade-credit / fused pattern.
        if customer.entity_type == "MSME":
            msme_out = msme.evaluate(customer, sig)
            reason_codes.extend(msme_out.drivers)
            if msme_out.intent_override and intent != intent_mod.DISTRESS:
                intent = msme_out.intent_override
                reason_codes.append("MSME_DOUBLE_GATE_DISTRESS")

        md = matrix_mod.lookup(tier, intent)

    direction = md.direction
    duration = md.duration
    auto_revert_at = None
    recommended = card.current_limit
    magnitude_pct = 0.0
    capacity_headroom = 0.0
    pipeline = "NONE"
    consent_status = "NA"
    consent_channel = None

    # ── Inactivity right-sizing (capital optimisation, §5.3) ────────────────
    if direction in {matrix_mod.MAINTAIN, matrix_mod.INCREASE} and tier != 4 and \
            guardrails.is_dormant(sig.utilization, card.months_inactive or 0, config):
        new_limit = guardrails.inactivity_rightsize(card.peak_drawn_12m, config)
        new_limit = max(new_limit, card.outstanding * (1 + config.decrease_buffer_pct))
        if new_limit < card.current_limit:
            direction = matrix_mod.DECREASE
            duration = matrix_mod.PERMANENT
            recommended = _round_to(new_limit, config.round_to)
            applied_caps.append("INACTIVITY_RIGHTSIZE")
            reason_codes = ["INACTIVITY_RIGHTSIZE"]
            md = matrix_mod.MatrixDecision(direction, duration, f"Tier {tier} · Inactivity",
                                           "Dormant undrawn limit right-sized")

    # ── Magnitude + formulas ────────────────────────────────────────────────
    if direction == matrix_mod.INCREASE:
        lo, hi = matrix_mod.magnitude_band(tier, sig.utilization, config)
        # Tier 3's utilisation bands are decrease-oriented; a Tier 3 × Growth cell
        # still warrants a cautious, capacity-capped bump rather than a hold.
        if hi <= 0:
            hi = config.cautious_increase_pct
        cap = guardrails.capacity_cap(sig.income_estimate, customer.external_debt,
                                      card.current_limit, config)
        capacity_headroom = cap.capacity_headroom
        target_frac = hi
        if cap.cap_frac < target_frac:
            target_frac = max(0.0, cap.cap_frac)
            applied_caps.append("CAPACITY_CAP")
        ctx = _leverage_context(db, customer, card, config)
        gate = guardrails.gate_increase(target_frac, ctx, config)
        applied_caps.extend(gate.applied_caps)
        if gate.blocked or gate.allowed_frac <= 0:
            direction = matrix_mod.MAINTAIN
            duration = matrix_mod.NA
            recommended = card.current_limit
            magnitude_pct = 0.0
        else:
            recommended = _round_to(card.current_limit * (1 + gate.allowed_frac), config.round_to)
            recommended = max(recommended, card.current_limit)
            magnitude_pct = (recommended / card.current_limit - 1) * 100 if card.current_limit else 0.0
            pipeline = "OFFER"
            consent_status = "PENDING_CONSENT"
            consent_channel = config.consent_channel
            if duration == matrix_mod.TEMPORARY:
                auto_revert_at = datetime.utcnow() + timedelta(days=SEASONAL_REVERT_DAYS)

    elif direction == matrix_mod.DECREASE and "INACTIVITY_RIGHTSIZE" not in applied_caps:
        # Decrease depth comes from intent severity, not the (decrease-only) util
        # band; high utilisation makes the cut *gentler* to avoid triggering
        # declines, and the buffer formula guarantees it never crosses outstanding.
        decrease_mult = matrix_mod.decrease_severity(tier, intent)
        if sig.utilization > 0.60:
            decrease_mult *= 0.7
        new_limit = guardrails.decrease_with_buffer(card.outstanding, card.current_limit,
                                                    decrease_mult, config)
        recommended = _round_to(new_limit, config.round_to)
        recommended = min(recommended, card.current_limit)
        magnitude_pct = (recommended / card.current_limit - 1) * 100 if card.current_limit else 0.0
        pipeline = "ACTION"

    elif direction == matrix_mod.DECREASE:  # inactivity path already set recommended
        magnitude_pct = (recommended / card.current_limit - 1) * 100 if card.current_limit else 0.0
        pipeline = "ACTION"

    # ── Re-score PD against the projected limit ─────────────────────────────
    risk_post = risk_mod.score(bureau_score=customer.bureau_score, sig=sig,
                               current_limit=card.current_limit,
                               projected_limit=recommended, config=config)
    pd_post = risk_post.pd_post_projected if not ko.hit else pd_pre

    # ── Confidence + review gating (§3.3, §11) ──────────────────────────────
    if ko.hit:
        confidence = 0.99
    else:
        confidence = round(
            0.6 * intent_conf + 0.25 * sig.income_confidence
            + 0.15 * (1 - min(pd_pre / 0.10, 1.0)), 3
        )

    review_required = False
    review_status = "NA"
    if not ko.hit:
        if pipeline == "OFFER" and confidence < config.auto_offer_min_confidence:
            review_required = True
            review_status = "PENDING"
            applied_caps.append("LOW_CONFIDENCE_REVIEW")
        elif direction == matrix_mod.DECREASE and confidence < config.manual_review_below:
            review_required = True
            review_status = "PENDING"
            applied_caps.append("LOW_CONFIDENCE_REVIEW")

    # ── Explainer ───────────────────────────────────────────────────────────
    revert_days = SEASONAL_REVERT_DAYS if auto_revert_at else None
    expl = explainer.render(
        direction=direction, duration=duration, intent=intent, tier=tier,
        matrix_cell=md.cell, current_limit=card.current_limit, recommended_limit=recommended,
        magnitude_pct=magnitude_pct, confidence=confidence, pd_pre=pd_pre, pd_post=pd_post,
        income_estimate=sig.income_estimate, reason_codes=reason_codes, applied_caps=applied_caps,
        pipeline=pipeline, auto_revert_days=revert_days,
    )

    snapshot = sig.snapshot()
    if msme_out is not None:
        snapshot["msme_double_gate"] = {
            "business_score": msme_out.business_score,
            "promoter_score": msme_out.promoter_score,
            "final_grade": msme_out.final_grade,
            "trade_distress": msme_out.trade_distress,
        }

    dec = Decision(
        id=f"CLR-DEC-{uuid.uuid4().hex[:8].upper()}",
        customer_id=customer.id, card_id=card.id, created_at=datetime.utcnow(),
        trigger_type=trigger_type, entity_type=customer.entity_type,
        tenant_archetype=config.archetype,
        risk_tier=tier, pd_pre=pd_pre, pd_post_projected=pd_post,
        intent=intent, intent_confidence=intent_conf, matrix_cell=md.cell,
        direction=direction, magnitude_pct=round(magnitude_pct, 2), duration=duration,
        confidence=confidence, auto_revert_at=auto_revert_at,
        current_limit=card.current_limit, recommended_limit=recommended,
        income_estimate=sig.income_estimate, external_debt=customer.external_debt,
        capacity_headroom=round(capacity_headroom, 0),
        reason_codes=reason_codes, knockouts=list(ko.triggered), applied_caps=applied_caps,
        signal_snapshot=snapshot,
        explainer_officer=expl.officer, explainer_customer=expl.customer, consent_copy=expl.consent,
        pipeline=pipeline, consent_status=consent_status, consent_channel=consent_channel,
        review_required=review_required, review_status=review_status,
        executed=False, customer_notified=False,
    )
    db.add(dec)
    db.add(AuditLog(
        entity_type="Decision", entity_id=dec.id, action="CREATED", actor="clr_engine",
        payload={
            "tier": tier, "intent": intent, "direction": direction,
            "magnitude_pct": round(magnitude_pct, 2), "duration": duration,
            "confidence": confidence, "pipeline": pipeline, "trigger": trigger_type,
            "reason_codes": reason_codes, "applied_caps": applied_caps,
        },
    ))
    db.commit()
    db.refresh(dec)
    return dec
