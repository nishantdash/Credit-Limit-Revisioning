"""Seed real customers + transactions from a raw CBS transaction export.

Loads `data/seed_transactions.csv` (a Hyperface CBS dump) on every boot so the
dashboard renders real-account data by default — alongside the synthetic
archetypes. One account_id → one bootstrapped customer + card; spend rows become
transactions, repayments inform the repayment baseline. Bulk-inserted in a single
commit to keep startup fast.

This intentionally mirrors the runtime /ingest path (same derivation), so what
loads at boot matches what an interactive upload would produce.
"""
import csv
import io
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from .models import Card, Customer, Transaction

CSV_PATH = Path(__file__).resolve().parent / "data" / "seed_transactions.csv"

# CBS transaction_type → how we treat the row.
SPEND_TYPES = {"SETTLEMENT_DEBIT", "SETTLEMENT_DEBIT_CASH"}
REPAY_TYPES = {"REPAYMENT"}

VALID_CATEGORIES = {"ESSENTIAL", "DISCRETIONARY", "ASPIRATIONAL"}

# MCC → category_class (ISO 18245 families, abbreviated to what appears in the dump).
_ESSENTIAL_MCC = {
    5411, 5412, 5422, 5451, 5462, 5499, 5300, 5310, 5311, 5541, 5542, 5983, 5172,
    4900, 4814, 4812, 4813, 4816, 4899, 5912, 5122, 8011, 8021, 8042, 8062, 8099,
    8211, 8220, 8241, 8299, 4111, 4121, 4131,
}
_ASPIRATIONAL_MCC = {
    4511, 4722, 4411, 7011, 7012, 7512, 5944, 5972, 7995, 5094, 5681, 5598, 5950,
    5811, 7991,
}


def _category_for_mcc(raw: str) -> str:
    try:
        m = int(raw)
    except (TypeError, ValueError):
        return "DISCRETIONARY"
    if 3000 <= m <= 3999 or m in _ASPIRATIONAL_MCC or 7010 <= m <= 7012:
        return "ASPIRATIONAL"
    if m in _ESSENTIAL_MCC:
        return "ESSENTIAL"
    return "DISCRETIONARY"


def _amount(raw: str) -> float | None:
    if not raw:
        return None
    try:
        return float(str(raw).replace(",", "").replace("₹", "").strip())
    except ValueError:
        return None


def _timestamp(raw: str) -> datetime:
    raw = (raw or "").strip()
    for fmt in ("%B %d, %Y, %I:%M %p", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return datetime.utcnow()


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _round_to(v: float, step: int) -> float:
    return float(round(v / step) * step)


def load(db: Session) -> int:
    """Bootstrap customers/cards/transactions from the CSV. Returns customers added."""
    if not CSV_PATH.exists():
        print(f"[csv_seed] {CSV_PATH} not found — skipping real-data load.")
        return 0

    text = CSV_PATH.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    # Bucket rows per account.
    buckets: dict[str, dict] = {}
    order: list[str] = []
    for row in reader:
        acct = (row.get("account_id") or "").strip()
        if not acct:
            continue
        if acct not in buckets:
            buckets[acct] = {"spend": [], "repay": 0.0, "card_id": (row.get("card_id") or "").strip()}
            order.append(acct)
        b = buckets[acct]
        ttype = (row.get("transaction_type") or "").strip().upper()
        amt = _amount(row.get("transaction_amount"))
        if amt is None:
            continue
        if ttype in REPAY_TYPES:
            b["repay"] += amt
        elif ttype in SPEND_TYPES:
            b["spend"].append({
                "id": (row.get("id") or "").strip(),
                "amount": amt,
                "category": _category_for_mcc(row.get("mcc")),
                "mcc": (row.get("mcc") or "").strip() or "UNKNOWN",
                "ts": _timestamp(row.get("txn_date")),
            })

    # Skip ids already present (e.g. the synthetic archetypes never collide, but be safe).
    existing = {c.id for c in db.query(Customer.id).all()}

    customers, cards, txns = [], [], []
    seen_txn: set[str] = set()
    for acct in order:
        if acct in existing:
            continue
        b = buckets[acct]
        spend_total = sum(s["amount"] for s in b["spend"])

        if spend_total > 0:
            income = _clamp(_round_to(spend_total / 0.35, 1000), 30_000, 1_500_000)
            limit = _clamp(_round_to(spend_total * 1.5, 5000), 50_000, 1_500_000)
        else:
            income, limit = 50_000.0, 100_000.0
        outstanding = _clamp(round(min(limit * 0.55, max(spend_total * 0.5, limit * 0.2))), 0, limit)
        # Real repayments drive the repayment baseline (→ a spread of risk tiers);
        # fall back to a neutral-healthy 90% payer when no repayment is present.
        last_payment = _clamp(round(b["repay"]), 0, outstanding) if b["repay"] > 0 else round(outstanding * 0.9, 2)

        customers.append(Customer(
            id=acct, name=acct, entity_type="RETAIL", segment="MASS",
            employment_type="SALARIED", programme_id="CBS-IMPORT",
            bureau_score=730, dpd_max_12m=0, account_vintage_months=12,
            stated_income=income, external_debt=0.0,
            fraud_flag=False, legal_block_flag=False, aa_consent_active=True,
        ))
        card_id = b["card_id"] or f"CARD-{acct[-12:]}"
        cards.append(Card(
            id=card_id, customer_id=acct, current_limit=limit, outstanding=outstanding,
            statement_balance=outstanding, last_payment=last_payment,
            min_due_last=round(outstanding * 0.05, 2), peak_drawn_12m=outstanding,
            months_since_last_change=12, months_inactive=0,
        ))
        for s in b["spend"]:
            tid = s["id"] or f"TXN-{acct[-8:]}-{len(txns)}"
            if tid in seen_txn:
                tid = f"{tid}-{len(txns)}"
            seen_txn.add(tid)
            cat = s["category"] if s["category"] in VALID_CATEGORIES else "ESSENTIAL"
            txns.append(Transaction(
                id=tid, card_id=card_id, amount=s["amount"], category_class=cat,
                merchant_category=s["mcc"], merchant_quality=0.6,
                is_recurring=False, is_declined=False, merchant_city=None, timestamp=s["ts"],
            ))

    db.add_all(customers)
    db.add_all(cards)
    db.add_all(txns)
    db.commit()
    print(f"[csv_seed] loaded {len(customers)} real customers, {len(txns)} spend txns from CBS export.")
    return len(customers)
