"""Tenant configuration — the configurable SaaS layer (§8).

Everything that encodes risk appetite or policy is externalised here, so a
conservative SFB and an aggressive NBFC run the same engine very differently
without code changes. Three archetype presets ship in the box; the active one
is persisted in the `tenant_config` table and loaded per request.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session


# ── Risk tier PD bands (§4.1) ────────────────────────────────────────────────
# Upper bound of each tier's target PD. Tier 4 is everything above Tier 3.
DEFAULT_TIER_PD_BANDS = {"tier1": 0.005, "tier2": 0.03, "tier3": 0.10}


# ── Risk × Utilisation magnitude bands (§4.3) ────────────────────────────────
# Magnitude *ranges* (signed fraction of current limit) keyed by tier and a
# utilisation band. Increases are additionally bounded by the capacity cap.
def _default_util_bands() -> dict[str, dict[str, list[float]]]:
    return {
        "1": {"high": [0.30, 0.50], "mod": [0.15, 0.25], "low": [0.0, 0.0]},
        "2": {"high": [0.15, 0.20], "mod": [0.0, 0.0], "low": [0.0, 0.0]},
        "3": {"high": [0.0, 0.0], "mod": [-0.40, -0.20], "low": [-0.70, -0.50]},
        "4": {"high": [-1.0, -1.0], "mod": [-1.0, -1.0], "low": [-1.0, -1.0]},
    }


@dataclass
class TenantConfig:
    name: str
    archetype: str  # BANK / NBFC / SFB

    # Layer weights (§2) — relative emphasis of each signal layer in scoring.
    layer_weights: dict[str, float] = field(default_factory=lambda: {
        "l1_repayment": 1.0,
        "l2_behavioural": 1.0,
        "l3_stability": 1.0,
        "l4_network": 0.5,
        "l5_liquidity": 1.0,
    })
    network_enabled: bool = False  # Layer 4 is opt-in, positive-only (§2.4)

    # Risk tiering
    tier_pd_bands: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_TIER_PD_BANDS))

    # Matrix magnitude bands (Risk × Utilisation modifier)
    util_bands: dict[str, dict[str, list[float]]] = field(default_factory=_default_util_bands)

    # Capacity caps (§5.1)
    max_dti: float = 0.45          # max debt-to-income for the affordability ceiling
    decrease_buffer_pct: float = 0.10   # operational buffer above outstanding (§5.2)
    inactivity_util_threshold: float = 0.05  # util below which a card is "dormant" (§5.3)
    inactivity_months: int = 12
    inactivity_peak_multiple: float = 1.5

    # Anti-spiral guardrails (§5.4)
    increase_frequency_gate_months: int = 6   # one increase per N months
    cooldown_months_after_decrease: int = 3
    per_customer_leverage_ceiling_pct: float = 0.40  # cumulative increase over rolling window
    leverage_window_months: int = 12
    portfolio_increase_velocity_cap_pct: float = 0.08  # max aggregate book uplift per sweep

    # Confidence gating (§3.3)
    auto_offer_min_confidence: float = 0.65   # below → route to nudge/observe or manual review
    manual_review_below: float = 0.45

    # Consent (§6)
    consent_channel: str = "OTP"   # OTP / MPIN
    aa_fetch_frequency: str = "ON_EVENT"

    # Cautious increase for the Tier 3 × Growth cell (§4.2) — a small, temporary
    # bump for a subprime customer showing genuine upward mobility, rather than
    # the conventional auto-cut. Capacity-capped like any other increase.
    cautious_increase_pct: float = 0.10

    # Magnitude smoothing
    round_to: float = 5000.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "archetype": self.archetype,
            "layer_weights": self.layer_weights,
            "network_enabled": self.network_enabled,
            "tier_pd_bands": self.tier_pd_bands,
            "util_bands": self.util_bands,
            "max_dti": self.max_dti,
            "decrease_buffer_pct": self.decrease_buffer_pct,
            "inactivity_util_threshold": self.inactivity_util_threshold,
            "inactivity_months": self.inactivity_months,
            "inactivity_peak_multiple": self.inactivity_peak_multiple,
            "increase_frequency_gate_months": self.increase_frequency_gate_months,
            "cooldown_months_after_decrease": self.cooldown_months_after_decrease,
            "per_customer_leverage_ceiling_pct": self.per_customer_leverage_ceiling_pct,
            "leverage_window_months": self.leverage_window_months,
            "portfolio_increase_velocity_cap_pct": self.portfolio_increase_velocity_cap_pct,
            "auto_offer_min_confidence": self.auto_offer_min_confidence,
            "manual_review_below": self.manual_review_below,
            "consent_channel": self.consent_channel,
            "aa_fetch_frequency": self.aa_fetch_frequency,
            "cautious_increase_pct": self.cautious_increase_pct,
            "round_to": self.round_to,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TenantConfig":
        base = cls(name=d.get("name", "Tenant"), archetype=d.get("archetype", "BANK"))
        for k, v in d.items():
            if hasattr(base, k) and v is not None:
                setattr(base, k, v)
        return base


# ── Archetype presets (§8.3) ─────────────────────────────────────────────────

def _bank() -> TenantConfig:
    """Large bank — balanced, capital-optimising. Tight guardrails, lower velocity cap."""
    return TenantConfig(
        name="Apex National Bank",
        archetype="BANK",
        layer_weights={"l1_repayment": 1.0, "l2_behavioural": 1.0, "l3_stability": 1.0,
                       "l4_network": 0.5, "l5_liquidity": 0.9},
        network_enabled=False,
        max_dti=0.45,
        increase_frequency_gate_months=6,
        per_customer_leverage_ceiling_pct=0.50,
        portfolio_increase_velocity_cap_pct=0.10,
        auto_offer_min_confidence=0.68,
    )


def _nbfc() -> TenantConfig:
    """NBFC — growth-led, higher yield. Wider bands, higher cap."""
    cfg = TenantConfig(
        name="Velocity Capital NBFC",
        archetype="NBFC",
        layer_weights={"l1_repayment": 0.9, "l2_behavioural": 1.2, "l3_stability": 1.0,
                       "l4_network": 0.8, "l5_liquidity": 1.1},
        network_enabled=True,
        max_dti=0.55,
        increase_frequency_gate_months=3,
        per_customer_leverage_ceiling_pct=0.75,
        portfolio_increase_velocity_cap_pct=0.15,
        auto_offer_min_confidence=0.58,
        cautious_increase_pct=0.15,
    )
    # NBFC runs hotter increase bands for Tier 1/2 growth.
    cfg.util_bands = _default_util_bands()
    cfg.util_bands["1"] = {"high": [0.40, 0.60], "mod": [0.20, 0.35], "low": [0.0, 0.10]}
    cfg.util_bands["2"] = {"high": [0.20, 0.30], "mod": [0.05, 0.15], "low": [0.0, 0.0]}
    return cfg


def _sfb() -> TenantConfig:
    """Small Finance Bank — inclusion-led, thin-file heavy. Conservative caps,
    strong distress watch, cautious Tier-3 mobility."""
    cfg = TenantConfig(
        name="Sahaj Small Finance Bank",
        archetype="SFB",
        layer_weights={"l1_repayment": 1.1, "l2_behavioural": 1.0, "l3_stability": 1.3,
                       "l4_network": 0.6, "l5_liquidity": 1.2},
        network_enabled=False,
        max_dti=0.40,
        decrease_buffer_pct=0.12,
        increase_frequency_gate_months=9,
        cooldown_months_after_decrease=4,
        per_customer_leverage_ceiling_pct=0.30,
        portfolio_increase_velocity_cap_pct=0.06,
        auto_offer_min_confidence=0.72,
        manual_review_below=0.50,
        cautious_increase_pct=0.08,
    )
    # SFB is gentler on subprime decreases (avoid triggering declines for thin-file).
    cfg.util_bands = _default_util_bands()
    cfg.util_bands["3"] = {"high": [0.0, 0.0], "mod": [-0.30, -0.15], "low": [-0.50, -0.30]}
    return cfg


PRESETS = {"BANK": _bank, "NBFC": _nbfc, "SFB": _sfb}


def preset(archetype: str) -> TenantConfig:
    factory = PRESETS.get(archetype.upper(), _bank)
    return factory()


# ── Persistence helpers ──────────────────────────────────────────────────────

def ensure_seeded(db: Session) -> None:
    """Make sure all three presets exist and one is active (BANK by default)."""
    from ..models import TenantConfig as TenantConfigRow

    existing = {row.archetype for row in db.query(TenantConfigRow).all()}
    for arch, factory in PRESETS.items():
        if arch not in existing:
            cfg = factory()
            db.add(TenantConfigRow(
                name=cfg.name,
                archetype=arch,
                active=(arch == "BANK"),
                config=cfg.to_dict(),
            ))
    if not db.query(TenantConfigRow).filter(TenantConfigRow.active.is_(True)).first():
        first = db.query(TenantConfigRow).filter(TenantConfigRow.archetype == "BANK").first()
        if first:
            first.active = True
    db.commit()


def load_active(db: Session) -> TenantConfig:
    from ..models import TenantConfig as TenantConfigRow

    row = db.query(TenantConfigRow).filter(TenantConfigRow.active.is_(True)).first()
    if not row:
        ensure_seeded(db)
        row = db.query(TenantConfigRow).filter(TenantConfigRow.active.is_(True)).first()
    return TenantConfig.from_dict(row.config) if row else preset("BANK")
