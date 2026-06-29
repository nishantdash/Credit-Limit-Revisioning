"""SQLAlchemy models for the intent-driven CLR engine.

The schema follows the concept note: customers carry the inputs to the five
signal layers + hard-knockout flags; decisions carry the four-part output
(direction, magnitude, duration, confidence) plus the intent, risk tier, and
which orchestration pipeline (offer vs action) they belong to.
"""
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .db import Base


class Customer(Base):
    __tablename__ = "customers"
    id = Column(String, primary_key=True)  # CIF-XXXX
    name = Column(String, nullable=False)
    entity_type = Column(String, default="RETAIL")  # RETAIL / MSME
    segment = Column(String, default="MASS")  # MASS / PREMIUM / THIN_FILE
    employment_type = Column(String, default="SALARIED")  # SALARIED / SELF_EMPLOYED / BUSINESS
    programme_id = Column(String, default="AU-LIT")

    # Layer 1 inputs (repayment & credit history)
    bureau_score = Column(Integer, nullable=False)
    dpd_max_12m = Column(Integer, default=0)
    account_vintage_months = Column(Integer, default=12)

    # Affordability inputs (capacity cap)
    stated_income = Column(Float, nullable=False)
    external_debt = Column(Float, default=0.0)  # other EMIs / obligations seen via AA

    # Hard-knockout flags (§2.6 — evaluated first, bypass scoring)
    fraud_flag = Column(Boolean, default=False)
    legal_block_flag = Column(Boolean, default=False)

    # Consent state (§6.3 — AA rail)
    aa_consent_active = Column(Boolean, default=True)

    # MSME-only fields (§9) — null for retail
    trade_dpd_days = Column(Integer, nullable=True)        # DPD on supplier invoices
    dscr = Column(Float, nullable=True)                    # debt-service coverage ratio
    working_capital_utilization = Column(Float, nullable=True)
    promoter_score = Column(Float, nullable=True)          # promoter personal score 0-100

    created_at = Column(DateTime, default=datetime.utcnow)

    cards = relationship("Card", back_populates="customer", cascade="all, delete-orphan")
    cashflow_signals = relationship("CashflowSignal", back_populates="customer", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="customer", cascade="all, delete-orphan")


class Card(Base):
    __tablename__ = "cards"
    id = Column(String, primary_key=True)  # CARD-XXXX
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    current_limit = Column(Float, nullable=False)
    outstanding = Column(Float, default=0.0)  # current drawn balance
    statement_balance = Column(Float, default=0.0)  # last statement total
    last_payment = Column(Float, default=0.0)  # amount paid against last statement
    min_due_last = Column(Float, default=0.0)  # minimum due on last statement
    peak_drawn_12m = Column(Float, default=0.0)  # peak outstanding in trailing 12m
    months_since_last_change = Column(Integer, default=12)
    months_inactive = Column(Integer, default=0)  # consecutive months util < 5%
    opened_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="cards")
    transactions = relationship("Transaction", back_populates="card", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True)
    card_id = Column(String, ForeignKey("cards.id"), nullable=False)
    amount = Column(Float, nullable=False)
    # Category-mix vector input (§2.2): essential / discretionary / aspirational
    category_class = Column(String, default="ESSENTIAL")
    merchant_category = Column(String)
    merchant_quality = Column(Float, default=0.6)  # 0-1 quality/consistency proxy
    is_recurring = Column(Boolean, default=False)  # subscriptions / mandates
    is_declined = Column(Boolean, default=False)   # high-value decline against limit
    merchant_city = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

    card = relationship("Card", back_populates="transactions")


class CashflowSignal(Base):
    """Layer 3 / Layer 5 inputs — inflows sourced via the AA rail."""
    __tablename__ = "cashflow_signals"
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    source = Column(String, nullable=False)  # CBS_SALARY / AA / UPI_INFLOW / GST / TRADE
    monthly_amount = Column(Float, nullable=False)
    regularity = Column(Float, default=0.8)  # 0-1: consistency/predictability of the inflow
    as_of = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="cashflow_signals")


class Decision(Base):
    __tablename__ = "decisions"
    id = Column(String, primary_key=True)  # CLR-DEC-XXXX
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    card_id = Column(String, ForeignKey("cards.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    trigger_type = Column(String, nullable=False)
    entity_type = Column(String, default="RETAIL")
    tenant_archetype = Column(String, default="BANK")

    # Risk
    risk_tier = Column(Integer, nullable=False)  # 1..4
    pd_pre = Column(Float, nullable=False)
    pd_post_projected = Column(Float, nullable=False)

    # Intent disambiguation (§3)
    intent = Column(String, nullable=False)  # GROWTH / DISTRESS / SEASONAL / NEUTRAL / KNOCKOUT
    intent_confidence = Column(Float, default=0.0)
    matrix_cell = Column(String, default="")  # e.g. "Tier 3 × Growth"

    # The four-part output (§3.3)
    direction = Column(String, nullable=False)  # INCREASE / DECREASE / MAINTAIN / FREEZE
    magnitude_pct = Column(Float, default=0.0)  # signed % change vs current limit
    duration = Column(String, default="NA")     # PERMANENT / TEMPORARY / NA
    confidence = Column(Float, default=0.0)
    auto_revert_at = Column(DateTime, nullable=True)  # for TEMPORARY (seasonal)

    current_limit = Column(Float, nullable=False)
    recommended_limit = Column(Float, nullable=False)

    # Affordability / capacity context
    income_estimate = Column(Float, default=0.0)
    external_debt = Column(Float, default=0.0)
    capacity_headroom = Column(Float, default=0.0)  # affordable limit ceiling

    # Explainability (§6.2)
    reason_codes = Column(JSON, default=list)
    knockouts = Column(JSON, default=list)
    applied_caps = Column(JSON, default=list)       # guardrails that bound the decision
    signal_snapshot = Column(JSON, default=dict)    # the 5-layer feature snapshot
    explainer_officer = Column(Text, default="")
    explainer_customer = Column(Text, default="")
    consent_copy = Column(Text, default="")         # consent-as-value-lever copy (offers)

    # Orchestration pipeline (§6.1 consent asymmetry)
    pipeline = Column(String, default="NONE")  # OFFER / ACTION / NONE
    # OFFER (increase): consent-gated, paused until OTP/MPIN
    consent_status = Column(String, default="NA")  # NA / PENDING_CONSENT / ACCEPTED / DECLINED
    consent_channel = Column(String, nullable=True)  # OTP / MPIN
    consent_decided_at = Column(DateTime, nullable=True)

    # Confidence gating → manual review (§3.3, §11)
    review_required = Column(Boolean, default=False)
    review_status = Column(String, default="NA")  # NA / PENDING / APPROVED / REJECTED
    review_by = Column(String, nullable=True)
    review_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)

    # Execution / write-back
    executed = Column(Boolean, default=False)
    executed_at = Column(DateTime, nullable=True)
    customer_notified = Column(Boolean, default=False)

    customer = relationship("Customer", back_populates="decisions")


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    actor = Column(String, default="system")
    payload = Column(JSON)


class TriggerEvent(Base):
    __tablename__ = "trigger_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    card_id = Column(String, ForeignKey("cards.id"), nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    decision_id = Column(String, ForeignKey("decisions.id"), nullable=True)


class TenantConfig(Base):
    """The configurable SaaS layer (§8). One row per archetype; exactly one is
    active. `config` holds the full externalised policy as JSON."""
    __tablename__ = "tenant_config"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    archetype = Column(String, nullable=False)  # BANK / NBFC / SFB
    active = Column(Boolean, default=False)
    config = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)
