from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Boolean,
    JSON,
    Text,
)
from sqlalchemy.orm import relationship
from .db import Base


class Customer(Base):
    __tablename__ = "customers"
    id = Column(String, primary_key=True)  # CIF-XXXX
    name = Column(String, nullable=False)
    segment = Column(String, nullable=False)  # MASS / PREMIUM
    bureau_score = Column(Integer, nullable=False)
    programme_id = Column(String, nullable=False)  # e.g., AU-LIT
    dpd_max_12m = Column(Integer, default=0)
    stated_income = Column(Float, nullable=False)
    employment_type = Column(String, default="SALARIED")  # SALARIED / SELF_EMPLOYED
    created_at = Column(DateTime, default=datetime.utcnow)

    cards = relationship("Card", back_populates="customer", cascade="all, delete-orphan")
    income_signals = relationship("IncomeSignal", back_populates="customer", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="customer", cascade="all, delete-orphan")


class Card(Base):
    __tablename__ = "cards"
    id = Column(String, primary_key=True)  # CARD-XXXX
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    current_limit = Column(Float, nullable=False)
    current_balance = Column(Float, default=0.0)
    benefits_tier = Column(String, default="SILVER")  # SILVER / GOLD / PLATINUM
    opened_at = Column(DateTime, default=datetime.utcnow)
    months_at_current_limit = Column(Integer, default=12)

    customer = relationship("Customer", back_populates="cards")
    transactions = relationship("Transaction", back_populates="card", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True)
    card_id = Column(String, ForeignKey("cards.id"), nullable=False)
    amount = Column(Float, nullable=False)
    merchant_category = Column(String)
    merchant_tier = Column(String, default="STANDARD")  # STANDARD / PREMIUM
    merchant_city = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

    card = relationship("Card", back_populates="transactions")


class IncomeSignal(Base):
    __tablename__ = "income_signals"
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    source = Column(String, nullable=False)  # CBS_SALARY / UPI_INFLOW / AA / GST
    monthly_amount = Column(Float, nullable=False)
    as_of = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="income_signals")


class Decision(Base):
    __tablename__ = "decisions"
    id = Column(String, primary_key=True)  # CLR-DEC-XXXX
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    card_id = Column(String, ForeignKey("cards.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    current_limit = Column(Float, nullable=False)
    recommended_limit = Column(Float, nullable=False)
    decision = Column(String, nullable=False)  # UPGRADE / DOWNGRADE / FREEZE
    confidence = Column(Float, nullable=False)
    pd_pre = Column(Float, nullable=False)
    pd_post_projected = Column(Float, nullable=False)
    income_estimate = Column(Float, nullable=False)
    behavioral_score = Column(Float, nullable=False)
    reason_codes = Column(JSON, nullable=False)
    explainer_text_officer = Column(Text, nullable=False)
    explainer_text_customer = Column(Text, nullable=False)
    trigger_type = Column(String, nullable=False)

    hitl_required = Column(Boolean, default=False)
    hitl_status = Column(String, default="N/A")  # N/A / PENDING / APPROVED / REJECTED
    hitl_decided_by = Column(String, nullable=True)
    hitl_decided_at = Column(DateTime, nullable=True)
    hitl_notes = Column(Text, nullable=True)

    benefits_tier_from = Column(String, nullable=True)
    benefits_tier_to = Column(String, nullable=True)

    executed = Column(Boolean, default=False)
    executed_at = Column(DateTime, nullable=True)
    customer_notified = Column(Boolean, default=False)
    customer_accepted = Column(Boolean, nullable=True)

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


class PolicyConfig(Base):
    __tablename__ = "policy_config"
    id = Column(Integer, primary_key=True, autoincrement=True)
    max_limit_multiple_of_income = Column(Float, default=3.0)
    hitl_threshold_inr = Column(Float, default=50000.0)
    min_months_at_current_limit = Column(Integer, default=6)
    max_dpd_eligible_12m = Column(Integer, default=60)
    pd_threshold_upgrade = Column(Float, default=0.05)
    auto_freeze_pd = Column(Float, default=0.08)
