"""Transaction-dump ingestion + cohort micro-review.

Accepts a CSV export from CBS for a specific customer cohort, attaches rows to
existing customers — and **bootstraps a new customer record for any ID not yet
in the roster** — then runs the intent engine over just that cohort so the bank
can pilot CLR against an arbitrary customer base from a raw dump.

Columns are matched case-insensitively and via common aliases (see
COLUMN_ALIASES), so a real CBS export usually works without renaming headers.
Only a customer-id column is required.

  customer_id        required   any string (cif / customer / customerid …)
  timestamp          optional   ISO-8601 / common date formats; defaults to now
  amount             optional   float (amt / txn_amount / value …)
  category_class     optional   ESSENTIAL | DISCRETIONARY | ASPIRATIONAL
  merchant_category  optional   free string, e.g. TRAVEL_INTL (mcc / merchant)
  merchant_city      optional   free string (city / location)

For IDs not in the roster, these optional columns seed the new customer's
profile (otherwise sensible values are derived from the uploaded spend):
  name               optional   display name (defaults to the id)
  stated_income      optional   monthly income (else derived from spend)
  current_limit      optional   card limit (else derived from spend)
  bureau_score       optional   300-900 (else 730)
  entity_type        optional   RETAIL | MSME (default RETAIL)
"""
import csv
import io
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..engine import config as cfg_mod
from ..engine import decision as decision_engine
from ..engine import orchestration
from ..models import AuditLog, Card, Customer, Decision, Transaction, TriggerEvent
from ..schemas import DecisionOut

router = APIRouter(prefix="/ingest", tags=["ingest"])

REQUIRED_COL = "customer_id"
MAX_ROWS = 10_000
MAX_COHORT_SWEEP = 250  # customers scored per cohort-sweep request (rest deferred)
VALID_CATEGORIES = {"ESSENTIAL", "DISCRETIONARY", "ASPIRATIONAL"}

# Normalised source header -> canonical field. Lets a raw CBS export map onto
# our schema without hand-renaming columns.
COLUMN_ALIASES = {
    "customer_id": "customer_id", "cif": "customer_id", "cif_id": "customer_id",
    "customer": "customer_id", "customerid": "customer_id", "cust_id": "customer_id",
    "account_id": "customer_id",
    "timestamp": "timestamp", "date": "timestamp", "txn_date": "timestamp",
    "transaction_date": "timestamp", "posting_date": "timestamp", "datetime": "timestamp",
    "amount": "amount", "amt": "amount", "txn_amount": "amount",
    "transaction_amount": "amount", "value": "amount", "spend": "amount",
    "category_class": "category_class", "category": "category_class", "class": "category_class",
    "merchant_category": "merchant_category", "mcc": "merchant_category", "merchant": "merchant_category",
    "merchant_city": "merchant_city", "city": "merchant_city", "location": "merchant_city",
    "name": "name", "customer_name": "name", "full_name": "name",
    "stated_income": "stated_income", "income": "stated_income", "monthly_income": "stated_income",
    "current_limit": "current_limit", "limit": "current_limit", "credit_limit": "current_limit",
    "bureau_score": "bureau_score", "cibil": "bureau_score", "credit_score": "bureau_score",
    "entity_type": "entity_type", "type": "entity_type",
}


class IngestSummary(BaseModel):
    rows_total: int
    rows_with_txn_data: int
    transactions_ingested: int
    cohort_customer_ids: list[str]
    known_customer_ids: list[str]
    created_customer_ids: list[str]
    unknown_customer_ids: list[str]
    errors: list[str]


class CohortSweepRequest(BaseModel):
    customer_ids: list[str]


class CohortSweepResponse(BaseModel):
    requested: int
    swept: int
    deferred: int  # over the per-request cap — re-run to sweep the rest
    skipped_unknown: list[str]
    decisions: list[DecisionOut]


def _norm(name: str) -> str:
    return (name or "").strip().lower().replace(" ", "_")


def _amount(raw: str) -> float | None:
    if not raw:
        return None
    try:
        return float(raw.replace(",", "").replace("₹", "").strip())
    except ValueError:
        return None


def _timestamp(raw: str) -> datetime:
    if not raw:
        return datetime.utcnow()
    raw = raw.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return datetime.utcnow()


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _round_to(v: float, step: int) -> float:
    return float(round(v / step) * step)


def _bootstrap_customer(db: Session, cif: str, rows: list[dict], profile: dict) -> tuple[Customer, Card]:
    """Create a brand-new customer + card for an ID not in the roster.

    Profile fields are taken from the upload where present, otherwise derived
    from observed spend so the decision engine has a plausible base to reason on.
    """
    spend = sum(r["amount"] for r in rows if r["amount"] is not None)

    income_in = _amount(profile.get("stated_income", ""))
    if income_in:
        income = _clamp(income_in, 15_000, 5_000_000)
    elif spend > 0:
        income = _clamp(_round_to(spend / 0.35, 1000), 30_000, 1_500_000)
    else:
        income = 50_000.0

    limit_in = _amount(profile.get("current_limit", ""))
    if limit_in:
        limit = _clamp(limit_in, 10_000, 5_000_000)
    elif spend > 0:
        limit = _clamp(_round_to(spend * 1.5, 5000), 50_000, 1_500_000)
    else:
        limit = 100_000.0

    raw_score = profile.get("bureau_score", "").strip()
    if raw_score:
        try:
            bureau = int(_clamp(int(float(raw_score)), 300, 900))
        except ValueError:
            bureau = 730
    else:
        bureau = 730  # neutral-good default for a new file with no score

    entity = (profile.get("entity_type", "") or "RETAIL").strip().upper()
    if entity not in ("RETAIL", "MSME"):
        entity = "RETAIL"

    cust = Customer(
        id=cif, name=(profile.get("name", "") or cif).strip(), entity_type=entity,
        segment="MASS", employment_type="SALARIED", programme_id="UPLOAD",
        bureau_score=bureau, dpd_max_12m=0, account_vintage_months=12,
        stated_income=income, external_debt=0.0,
        fraud_flag=False, legal_block_flag=False, aa_consent_active=True,
    )
    db.add(cust)
    db.flush()

    outstanding = _clamp(round(min(limit * 0.55, max(spend * 0.5, limit * 0.2))), 0, limit)
    # A brand-new account has no repayment track record, so seed a neutral-healthy
    # baseline (pays ~90% of statement → pqr ≈ 0.9, low min-due dependency). This
    # keeps risk mid-range and lets the customer's *actual uploaded spend* drive
    # the intent layer — the differentiator CLR is built around.
    card = Card(
        id=f"CARD-UP-{uuid.uuid4().hex[:8].upper()}", customer_id=cif,
        current_limit=limit, outstanding=outstanding, statement_balance=outstanding,
        last_payment=round(outstanding * 0.9, 2), min_due_last=round(outstanding * 0.05, 2),
        peak_drawn_12m=outstanding, months_since_last_change=12, months_inactive=0,
    )
    db.add(card)
    db.flush()
    return cust, card


@router.post("/transactions-csv", response_model=IngestSummary)
async def upload_transactions_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Upload a .csv file")
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(400, "File must be UTF-8 encoded")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(400, "CSV has no header row")
    # Map each source header onto a canonical field via the alias table.
    field_to_header: dict[str, str] = {}
    for h in reader.fieldnames:
        canon = COLUMN_ALIASES.get(_norm(h))
        if canon and canon not in field_to_header:
            field_to_header[canon] = h
    if REQUIRED_COL not in field_to_header:
        raise HTTPException(
            400,
            "CSV must contain a customer-id column (customer_id, cif, customer, …). "
            f"Found headers: {reader.fieldnames}",
        )

    def cell(row: dict, field: str) -> str:
        h = field_to_header.get(field)
        return (row.get(h) if h else None) or ""

    PROFILE_FIELDS = ("name", "stated_income", "current_limit", "bureau_score", "entity_type")

    # ── Pass 1 — parse rows, bucket per customer (preserving first-seen order) ──
    buckets: dict[str, dict] = {}
    order: list[str] = []
    errors: list[str] = []
    rows_total = 0
    for idx, row in enumerate(reader, start=2):
        rows_total += 1
        if rows_total > MAX_ROWS:
            errors.append(f"Stopped at {MAX_ROWS} rows — upload smaller chunks")
            break
        cif = cell(row, REQUIRED_COL).strip()
        if not cif:
            errors.append(f"Row {idx}: empty customer_id")
            continue
        if cif not in buckets:
            buckets[cif] = {"rows": [], "profile": {}}
            order.append(cif)
        bucket = buckets[cif]
        # First non-empty value for each profile hint wins.
        for f in PROFILE_FIELDS:
            if f not in bucket["profile"]:
                v = cell(row, f).strip()
                if v:
                    bucket["profile"][f] = v
        amount = _amount(cell(row, "amount"))
        cat = (cell(row, "category_class") or "ESSENTIAL").strip().upper()
        if cat not in VALID_CATEGORIES:
            cat = "ESSENTIAL"
        bucket["rows"].append({
            "amount": amount,
            "category_class": cat,
            "merchant_category": (cell(row, "merchant_category") or "UNKNOWN").strip().upper(),
            "merchant_city": (cell(row, "merchant_city").strip() or None),
            "timestamp": _timestamp(cell(row, "timestamp")),
        })

    # ── Pass 2 — attach to existing customers, bootstrap new ones ──
    known: list[str] = []
    created: list[str] = []
    rows_with_txn = txns_added = 0
    for cif in order:
        bucket = buckets[cif]
        cust = db.query(Customer).filter(Customer.id == cif).first()
        if cust is None:
            cust, card = _bootstrap_customer(db, cif, bucket["rows"], bucket["profile"])
            created.append(cif)
        else:
            known.append(cif)
            card = cust.cards[0] if cust.cards else None
        if card is None:
            continue
        for r in bucket["rows"]:
            if r["amount"] is None:
                continue
            rows_with_txn += 1
            db.add(Transaction(
                id=f"TXN-UP-{uuid.uuid4().hex[:10].upper()}",
                card_id=card.id, amount=r["amount"], category_class=r["category_class"],
                merchant_category=r["merchant_category"], merchant_city=r["merchant_city"],
                timestamp=r["timestamp"],
            ))
            txns_added += 1

    db.add(AuditLog(entity_type="Ingest", entity_id=file.filename, action="CSV_UPLOAD",
                    actor="dashboard_user",
                    payload={"rows_total": rows_total, "transactions_ingested": txns_added,
                             "cohort_size": len(buckets), "attached": len(known),
                             "created": len(created)}))
    db.commit()
    # Created customers join the cohort so the existing "Run CLR" sweep covers them.
    return IngestSummary(
        rows_total=rows_total, rows_with_txn_data=rows_with_txn, transactions_ingested=txns_added,
        cohort_customer_ids=sorted(buckets.keys()),
        known_customer_ids=sorted(known + created),
        created_customer_ids=sorted(created),
        unknown_customer_ids=[], errors=errors,
    )


@router.post("/cohort-sweep", response_model=CohortSweepResponse)
def cohort_sweep(req: CohortSweepRequest, db: Session = Depends(get_db)):
    if not req.customer_ids:
        raise HTTPException(400, "customer_ids cannot be empty")
    # Each decision is a full engine run + DB commit (~0.1-0.8s). Cap the work per
    # request so a multi-thousand-row upload can't run for an hour and time out the
    # browser — the caller re-runs to sweep the deferred remainder.
    to_sweep = req.customer_ids[:MAX_COHORT_SWEEP]
    deferred = max(0, len(req.customer_ids) - len(to_sweep))
    config = cfg_mod.load_active(db)
    decisions: list[Decision] = []
    skipped: list[str] = []
    for cif in to_sweep:
        customer = db.query(Customer).filter(Customer.id == cif).first()
        if not customer or not customer.cards:
            skipped.append(cif)
            continue
        card = customer.cards[0]
        evt = TriggerEvent(card_id=card.id, event_type="COHORT_SWEEP",
                           payload={"sweep_at": datetime.utcnow().isoformat(), "uploaded": True})
        db.add(evt)
        db.flush()
        dec = decision_engine.decide(db, customer_id=cif, trigger_type="COHORT_SWEEP", config=config)
        evt.decision_id = dec.id
        orchestration.auto_orchestrate(db, dec)
        decisions.append(dec)

    db.add(AuditLog(entity_type="Ingest", entity_id="cohort-sweep", action="COHORT_SWEEP_RUN",
                    actor="dashboard_user",
                    payload={"requested": len(req.customer_ids), "swept": len(decisions),
                             "deferred": deferred, "skipped_unknown": skipped}))
    db.commit()
    for d in decisions:
        db.refresh(d)
    return CohortSweepResponse(
        requested=len(req.customer_ids), swept=len(decisions), deferred=deferred,
        skipped_unknown=skipped,
        decisions=[DecisionOut.model_validate(d) for d in decisions],
    )


@router.get("/sample-csv")
def sample_csv():
    from fastapi.responses import PlainTextResponse
    # CIF-1001/1003 attach to existing roster customers; NEW-9001 is an ID not
    # in the roster — it gets a customer record bootstrapped from the `name`
    # column + its uploaded spend.
    lines = [
        "customer_id,name,timestamp,amount,category_class,merchant_category,merchant_city",
        "CIF-1001,,2026-06-20T14:23:11,4500.00,ASPIRATIONAL,FINE_DINING,Bengaluru",
        "CIF-1001,,2026-06-21T09:15:00,1200.00,ESSENTIAL,GROCERY,Bengaluru",
        "CIF-1003,,2026-06-22T18:40:00,8800.00,ASPIRATIONAL,TRAVEL_INTL,Mumbai",
        "NEW-9001,Riya Malhotra,2026-06-22T11:00:00,21000.00,ASPIRATIONAL,LUXURY_RETAIL,Delhi",
        "NEW-9001,Riya Malhotra,2026-06-24T19:30:00,7300.00,DISCRETIONARY,FINE_DINING,Delhi",
        "NEW-9001,Riya Malhotra,2026-06-26T08:10:00,2600.00,ESSENTIAL,GROCERY,Delhi",
    ]
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/csv",
                             headers={"Content-Disposition": 'attachment; filename="clr_sample_dump.csv"'})
