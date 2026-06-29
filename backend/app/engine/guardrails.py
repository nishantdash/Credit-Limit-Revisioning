"""Decision formulas and guardrails (§5).

The matrix produces a direction and a magnitude band. These formulas then bound
it so the engine cannot manufacture the very risk it exists to control:

  §5.1  Proactive increase  — capacity-cap model (affordability ceiling)
  §5.2  Risk-based decrease  — exposure minimisation with operational buffer
  §5.3  Inactivity decrease  — capital optimisation anchored to recent peak
  §5.4  Anti-spiral guardrail — frequency gates, per-customer leverage ceiling,
        portfolio increase-velocity cap, post-decrease cooldown
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import config as cfg_mod


@dataclass
class CapacityResult:
    capacity_headroom: float   # affordable limit ceiling (absolute ₹)
    cap_frac: float            # max fractional increase vs current limit


def capacity_cap(income_monthly: float, external_debt_monthly: float,
                 current_limit: float, config: cfg_mod.TenantConfig) -> CapacityResult:
    """§5.1 — every increase is bounded by estimated financial capacity, so a
    growth signal can never push a customer past affordability.

        Δ = min(Matrix_Max, [(Est_Income × Max_DTI) − External_Debt] ÷ CL_current − 1)

    Income and debt are annualised; both are sourced in real time via the AA rail.
    """
    affordable = max(0.0, income_monthly * 12.0 * config.max_dti - external_debt_monthly * 12.0)
    cap_frac = (affordable / current_limit - 1.0) if current_limit else 0.0
    return CapacityResult(capacity_headroom=affordable, cap_frac=cap_frac)


def decrease_with_buffer(outstanding: float, current_limit: float, decrease_mult: float,
                         config: cfg_mod.TenantConfig) -> float:
    """§5.2 — apply a decrease without triggering over-limit fees or declines, by
    holding an operational buffer above current outstanding.

        CL_new = max(Outstanding × (1 + buffer), CL_current × (1 − Decrease_Mult))
    """
    buffer = 1.0 + config.decrease_buffer_pct
    return max(outstanding * buffer, current_limit * (1.0 - abs(decrease_mult)))


def inactivity_rightsize(peak_drawn_12m: float, config: cfg_mod.TenantConfig) -> float:
    """§5.3 — dormant undrawn limits are right-sized to free regulatory capital,
    anchored to the customer's own recent peak so the change is never punitive.

        CL_new = Peak_Utilization_last_12m × peak_multiple
    """
    return peak_drawn_12m * config.inactivity_peak_multiple


def is_dormant(utilization: float, months_inactive: int, config: cfg_mod.TenantConfig) -> bool:
    return utilization < config.inactivity_util_threshold and months_inactive >= config.inactivity_months


@dataclass
class GuardrailContext:
    months_since_last_change: int
    recently_decreased: bool
    customer_cumulative_increase_frac: float  # over the rolling leverage window
    portfolio_increase_used_frac: float       # share of book uplift already extended this run
    portfolio_increase_cap_frac: float        # = config.portfolio_increase_velocity_cap_pct


@dataclass
class GuardrailResult:
    allowed_frac: float
    blocked: bool
    applied_caps: list[str] = field(default_factory=list)


def gate_increase(proposed_frac: float, ctx: GuardrailContext,
                  config: cfg_mod.TenantConfig) -> GuardrailResult:
    """§5.4 — cap the engine's own increase behaviour."""
    caps: list[str] = []
    frac = max(0.0, proposed_frac)

    # Frequency gate — at most one increase per N months.
    if ctx.months_since_last_change < config.increase_frequency_gate_months:
        caps.append("FREQUENCY_GATE")
        return GuardrailResult(allowed_frac=0.0, blocked=True, applied_caps=caps)

    # Post-decrease cooldown — don't yo-yo a customer just cut for risk.
    if ctx.recently_decreased and ctx.months_since_last_change < config.cooldown_months_after_decrease:
        caps.append("POST_DECREASE_COOLDOWN")
        return GuardrailResult(allowed_frac=0.0, blocked=True, applied_caps=caps)

    # Per-customer leverage ceiling — cumulative increases over a rolling window
    # are bounded regardless of how many positive signals fire.
    remaining_leverage = config.per_customer_leverage_ceiling_pct - ctx.customer_cumulative_increase_frac
    if remaining_leverage <= 0:
        caps.append("LEVERAGE_CEILING")
        return GuardrailResult(allowed_frac=0.0, blocked=True, applied_caps=caps)
    if frac > remaining_leverage:
        frac = remaining_leverage
        caps.append("LEVERAGE_CEILING")

    # System-level increase-velocity cap — a ceiling on aggregate book uplift per
    # unit time, independent of individual eligibility.
    portfolio_remaining = ctx.portfolio_increase_cap_frac - ctx.portfolio_increase_used_frac
    if portfolio_remaining <= 0:
        caps.append("PORTFOLIO_VELOCITY_CAP")
        return GuardrailResult(allowed_frac=0.0, blocked=True, applied_caps=caps)

    return GuardrailResult(allowed_frac=frac, blocked=False, applied_caps=caps)
