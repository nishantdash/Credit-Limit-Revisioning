"""L2d — GenAI explainer (template-based stand-in).

Renders reason codes into officer-facing and customer-facing copy. In
production this calls a Claude/GPT-class LLM with structured prompt templates;
the prototype uses deterministic templates so the demo is hermetic.
"""
from dataclasses import dataclass


REASON_TEXT = {
    "INCOME_GROWTH": "estimated monthly income has grown",
    "REPAYMENT_STREAK": "consistent on-time payments over the last 12 months",
    "UTILIZATION_STABLE": "stable, healthy utilisation pattern",
    "HEALTHY_UTILIZATION": "utilisation sits in the healthy 30-60% band",
    "PREMIUM_MERCHANT_MIX": "spend mix has moved toward premium merchants",
    "SPEND_VELOCITY_UP": "30-day spend has accelerated meaningfully",
    "SPEND_VELOCITY_DOWN": "30-day spend has dropped — competitor wallet share risk",
    "HIGH_UTILIZATION": "sustained high utilisation indicating stress",
    "CARD_USAGE_DECLINING": "card usage has fallen sharply",
    "PAST_DUE_HISTORY": "past-due history within the last 12 months",
    "INCOME_STEPCHANGE": "live cashflow shows a step-change in income",
    "POLICY_VIOLATION_DPD": "DPD history breaches the bank's eligibility policy",
    "POLICY_VIOLATION_TENURE": "card has not held the current limit for the required minimum tenure",
    "POLICY_VIOLATION_INCOME_CAP": "requested limit exceeds the income multiple cap",
    "PD_OVER_THRESHOLD": "modelled PD exceeds the bank's upgrade threshold",
}


@dataclass
class ExplainerOutput:
    officer_text: str
    customer_text: str


def render(
    *,
    decision: str,
    current_limit: float,
    recommended_limit: float,
    reason_codes: list[str],
    behavioral_score: float,
    behavior_delta_signals: list[str],
    income_estimate: float,
    income_delta_pct: float,
    pd_pre: float,
    pd_post: float,
    benefits_tier_from: str | None,
    benefits_tier_to: str | None,
) -> ExplainerOutput:
    reason_bits = [REASON_TEXT.get(r, r) for r in reason_codes]
    reasons_clause = "; ".join(reason_bits) if reason_bits else "no notable signals"

    delta = recommended_limit - current_limit
    pct = (delta / current_limit * 100) if current_limit else 0.0

    if decision == "UPGRADE":
        officer = (
            f"UPGRADE recommended: ₹{current_limit:,.0f} → ₹{recommended_limit:,.0f} "
            f"(+₹{delta:,.0f}, +{pct:.1f}%). "
            f"Behavioral score {behavioral_score:.0f}/100. "
            f"Income estimate ₹{income_estimate:,.0f}/mo ({income_delta_pct:+.1f}% vs stated). "
            f"PD {pd_pre:.2%} → {pd_post:.2%}. "
            f"Drivers: {reasons_clause}."
        )
        if benefits_tier_from and benefits_tier_to and benefits_tier_from != benefits_tier_to:
            officer += f" Benefits tier auto-upgrade {benefits_tier_from} → {benefits_tier_to}."
        customer = (
            f"Good news — your credit limit has been increased to ₹{recommended_limit:,.0f}. "
            f"This is because of {reasons_clause}."
        )
        if benefits_tier_to and benefits_tier_from != benefits_tier_to:
            customer += f" You've also been upgraded to the {benefits_tier_to} benefits tier."

    elif decision == "DOWNGRADE":
        officer = (
            f"DOWNGRADE recommended: ₹{current_limit:,.0f} → ₹{recommended_limit:,.0f} "
            f"({pct:+.1f}%). Behavioral score {behavioral_score:.0f}/100 "
            f"(direction concerns: {', '.join(behavior_delta_signals) or 'none'}). "
            f"PD {pd_pre:.2%} → {pd_post:.2%}. Drivers: {reasons_clause}."
        )
        customer = (
            "We've made a temporary adjustment to your credit limit to better align "
            "with your recent account activity. You can review the details in-app."
        )

    else:  # FREEZE
        officer = (
            f"FREEZE: holding limit at ₹{current_limit:,.0f}. "
            f"Behavioral score {behavioral_score:.0f}/100. "
            f"PD {pd_pre:.2%}. Drivers: {reasons_clause}."
        )
        customer = "Your credit limit remains unchanged at this time."

    return ExplainerOutput(officer_text=officer, customer_text=customer)
