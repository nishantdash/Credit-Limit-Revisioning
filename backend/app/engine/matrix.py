"""The reframed decision matrix: Risk × Intent (§4.2).

The conventional matrix is Risk × Utilisation. This product's primary matrix is
Risk × Intent, with utilisation demoted to a magnitude modifier (§4.3). The
single most important structural change is the Tier 3 × Growth cell: a subprime
customer showing genuine upward mobility is a future Tier 2 customer, so the
engine holds or cautiously/temporarily extends instead of auto-cutting.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import config as cfg_mod
from . import intent as intent_mod

INCREASE = "INCREASE"
DECREASE = "DECREASE"
MAINTAIN = "MAINTAIN"
FREEZE = "FREEZE"

PERMANENT = "PERMANENT"
TEMPORARY = "TEMPORARY"
NA = "NA"


@dataclass
class MatrixDecision:
    direction: str
    duration: str
    cell: str           # human label, e.g. "Tier 3 × Growth"
    note: str           # the policy intent of the cell


# (direction, duration, note) keyed by (tier, intent). Magnitude comes from the
# utilisation-modifier bands in the tenant config, then the capacity/decrease
# formulas bound it.
_MATRIX: dict[tuple[int, str], tuple[str, str, str]] = {
    (1, intent_mod.GROWTH):   (INCREASE, PERMANENT, "Aggressive increase — instant, permanent"),
    (1, intent_mod.NEUTRAL):  (MAINTAIN, NA, "Maintain"),
    (1, intent_mod.DISTRESS): (MAINTAIN, NA, "Hold + observe (likely seasonal)"),
    (1, intent_mod.SEASONAL): (INCREASE, TEMPORARY, "Temporary festive increase, auto-reverts"),

    (2, intent_mod.GROWTH):   (INCREASE, PERMANENT, "Moderate increase, step-up"),
    (2, intent_mod.NEUTRAL):  (MAINTAIN, NA, "Maintain"),
    (2, intent_mod.DISTRESS): (MAINTAIN, NA, "Hold + soft engage; freeze velocity"),
    (2, intent_mod.SEASONAL): (INCREASE, TEMPORARY, "Temporary increase, auto-reverts"),

    (3, intent_mod.GROWTH):   (INCREASE, TEMPORARY, "Cautious temporary increase (do not auto-cut a growing customer)"),
    (3, intent_mod.NEUTRAL):  (DECREASE, PERMANENT, "Decrease slowly"),
    (3, intent_mod.DISTRESS): (DECREASE, PERMANENT, "Decrease sharply + restructure offer"),
    (3, intent_mod.SEASONAL): (MAINTAIN, NA, "Hold — observe before extending"),

    (4, intent_mod.GROWTH):   (FREEZE, NA, "Freeze regardless of intent"),
    (4, intent_mod.NEUTRAL):  (FREEZE, NA, "Freeze"),
    (4, intent_mod.DISTRESS): (DECREASE, PERMANENT, "Collapse to obligation"),
    (4, intent_mod.SEASONAL): (FREEZE, NA, "Freeze"),
}


def util_band_key(utilization: float) -> str:
    if utilization > 0.60:
        return "high"
    if utilization >= 0.15:
        return "mod"
    return "low"


def lookup(tier: int, intent: str) -> MatrixDecision:
    direction, duration, note = _MATRIX[(tier, intent)]
    cell = f"Tier {tier} × {intent.capitalize()}"
    return MatrixDecision(direction=direction, duration=duration, cell=cell, note=note)


def magnitude_band(tier: int, utilization: float, config: cfg_mod.TenantConfig) -> tuple[float, float]:
    """The utilisation-modifier band for this tier (signed fractions of limit)."""
    band = config.util_bands.get(str(tier), {})
    lo, hi = band.get(util_band_key(utilization), [0.0, 0.0])
    return lo, hi


# Decrease depth by (tier, intent). Utilisation modulates this (§4.3): high util
# argues for a *gentler* decrease to avoid triggering declines — the buffer
# formula then guarantees the cut never crosses outstanding + buffer.
_DECREASE_SEVERITY = {
    (3, intent_mod.NEUTRAL): 0.20,
    (3, intent_mod.DISTRESS): 0.35,
    (4, intent_mod.DISTRESS): 0.50,   # collapse toward obligation
}


def decrease_severity(tier: int, intent: str) -> float:
    return _DECREASE_SEVERITY.get((tier, intent), 0.40)
