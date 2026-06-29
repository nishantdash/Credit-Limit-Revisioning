from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    entity_type: str
    segment: str
    employment_type: str
    programme_id: str
    bureau_score: int
    dpd_max_12m: int
    account_vintage_months: int
    stated_income: float
    external_debt: float
    fraud_flag: bool
    legal_block_flag: bool
    aa_consent_active: bool
    trade_dpd_days: Optional[int] = None
    dscr: Optional[float] = None
    working_capital_utilization: Optional[float] = None


class CardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    customer_id: str
    current_limit: float
    outstanding: float
    statement_balance: float
    last_payment: float
    min_due_last: float
    peak_drawn_12m: float
    months_since_last_change: int
    months_inactive: int


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    customer_id: str
    card_id: str
    created_at: datetime
    trigger_type: str
    entity_type: str
    tenant_archetype: str

    risk_tier: int
    pd_pre: float
    pd_post_projected: float

    intent: str
    intent_confidence: float
    matrix_cell: str

    direction: str
    magnitude_pct: float
    duration: str
    confidence: float
    auto_revert_at: Optional[datetime] = None

    current_limit: float
    recommended_limit: float
    income_estimate: float
    external_debt: float
    capacity_headroom: float

    reason_codes: list[str]
    knockouts: list[str]
    applied_caps: list[str]
    signal_snapshot: dict[str, Any]
    explainer_officer: str
    explainer_customer: str
    consent_copy: str

    pipeline: str
    consent_status: str
    consent_channel: Optional[str] = None
    consent_decided_at: Optional[datetime] = None

    review_required: bool
    review_status: str
    review_by: Optional[str] = None
    review_at: Optional[datetime] = None

    executed: bool
    executed_at: Optional[datetime] = None
    customer_notified: bool


class ReviewAction(BaseModel):
    actor: str
    notes: Optional[str] = None


class ConsentAction(BaseModel):
    actor: str = "customer"
    channel: Optional[str] = None  # OTP / MPIN
    notes: Optional[str] = None


class TriggerRequest(BaseModel):
    card_id: str
    event_type: str
    payload: Optional[dict[str, Any]] = None


class WebhookEvent(BaseModel):
    event_type: str
    card_id: str
    outstanding: Optional[float] = None
    statement_balance: Optional[float] = None
    last_payment: Optional[float] = None
    min_due_last: Optional[float] = None
    aa_consent_active: Optional[bool] = None
    timestamp: Optional[datetime] = None


class ConfigSwitch(BaseModel):
    archetype: str  # BANK / NBFC / SFB


class ConfigPatch(BaseModel):
    config: dict[str, Any]


# ── Analytics ───────────────────────────────────────────────────────────────

class FunnelMetrics(BaseModel):
    customers: int
    reviewed: int
    by_intent: dict[str, int]
    by_tier: dict[str, int]
    by_direction: dict[str, int]
    offers_pending_consent: int
    offers_accepted: int
    actions_applied: int
    review_pending: int
    knockouts: int


class RoiMetrics(BaseModel):
    offered_uplift_inr: float
    activated_uplift_inr: float
    exposure_reduced_inr: float
    avg_pd_pre: float
    avg_pd_post: float
    increases: int
    decreases: int
    temporary_offers: int
    estimated_incremental_interchange_monthly_inr: float


class GuardrailStatus(BaseModel):
    portfolio_increase_cap_pct: float
    portfolio_increase_used_pct: float
    portfolio_headroom_pct: float
    total_book_limit_inr: float
    increase_extended_30d_inr: float
    decisions_capped: int
    cap_breakdown: dict[str, int]
