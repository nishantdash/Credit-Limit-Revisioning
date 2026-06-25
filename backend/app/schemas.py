from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    segment: str
    bureau_score: int
    programme_id: str
    dpd_max_12m: int
    stated_income: float
    employment_type: str


class CardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    customer_id: str
    current_limit: float
    current_balance: float
    benefits_tier: str
    months_at_current_limit: int


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    customer_id: str
    card_id: str
    created_at: datetime
    current_limit: float
    recommended_limit: float
    decision: str
    confidence: float
    pd_pre: float
    pd_post_projected: float
    income_estimate: float
    behavioral_score: float
    reason_codes: list[str]
    explainer_text_officer: str
    explainer_text_customer: str
    trigger_type: str
    hitl_required: bool
    hitl_status: str
    hitl_decided_by: Optional[str]
    hitl_decided_at: Optional[datetime]
    benefits_tier_from: Optional[str]
    benefits_tier_to: Optional[str]
    executed: bool
    executed_at: Optional[datetime]
    customer_notified: bool
    customer_accepted: Optional[bool]


class HitlAction(BaseModel):
    actor: str
    notes: Optional[str] = None


class TriggerRequest(BaseModel):
    card_id: str
    event_type: str  # CARD_UTILIZATION_THRESHOLD / SPEND_SPIKE_DETECTED / INCOME_STEPCHANGE / PERIODIC_SWEEP
    payload: Optional[dict[str, Any]] = None


class WebhookEvent(BaseModel):
    event_type: str
    card_id: str
    customer_id: Optional[str] = None
    programme_id: Optional[str] = None
    current_limit: Optional[float] = None
    current_balance: Optional[float] = None
    utilization_pct: Optional[float] = None
    rolling_30d_spend: Optional[float] = None
    prior_30d_spend: Optional[float] = None
    spike_pct: Optional[float] = None
    timestamp: Optional[datetime] = None


class FunnelMetrics(BaseModel):
    eligible: int
    reviewed: int
    upgrade_recommended: int
    downgrade_recommended: int
    freeze_recommended: int
    hitl_pending: int
    executed: int
    customer_notified: int
    customer_accepted: int


class RoiMetrics(BaseModel):
    total_limit_uplift_inr: float
    avg_pd_pre: float
    avg_pd_post: float
    upgrades_count: int
    downgrades_count: int
    benefits_tier_upgrades: int
    estimated_incremental_interchange_monthly_inr: float
