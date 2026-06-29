"""Hard-knockout layer (§2.6) — evaluated first, bypasses scoring.

Any hit forces a freeze/decrease path and skips the intent model entirely.
The account is placed in Tier 4 instantly.
"""
from dataclasses import dataclass

from ..models import Customer


@dataclass
class KnockoutResult:
    triggered: list[str]

    @property
    def hit(self) -> bool:
        return bool(self.triggered)


def evaluate(customer: Customer) -> KnockoutResult:
    triggered: list[str] = []
    if customer.fraud_flag:
        triggered.append("KNOCKOUT_FRAUD")
    if customer.legal_block_flag:
        triggered.append("KNOCKOUT_LEGAL_BLOCK")
    if (customer.dpd_max_12m or 0) >= 30:
        triggered.append("KNOCKOUT_DPD_30_PLUS")
    return KnockoutResult(triggered=triggered)
