"""L1 — Transaction-dump ingestion.

Accepts a CSV upload representing a bank's transaction export for a specific
customer cohort. Attaches rows to existing customers, returns a validation
summary, and (optionally) fires a cohort sweep through the L3 trigger engine
so the bank can see decisions for *just* that uploaded customer base.

Expected columns (case-insensitive, only customer_id required if you just
want to scope a sweep with no new transactions):

  customer_id          required        CIF-XXXX
  timestamp            optional        ISO-8601; defaults to now if missing
  amount               optional        float
  merchant_category    optional        free string, e.g. FINE_DINING
  merchant_tier        optional        STANDARD | PREMIUM
  merchant_city        optional        free string
"""
import csv
import io
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..engine import decision as decision_engine
from ..engine.hitl_executor import auto_execute_if_eligible
from ..models import AuditLog, Card, Customer, Decision, Transaction, TriggerEvent
from ..schemas import DecisionOut

router = APIRouter(prefix="/ingest", tags=["ingest"])

REQUIRED_COL = "customer_id"
OPTIONAL_TXN_COLS = {"timestamp", "amount", "merchant_category", "merchant_tier", "merchant_city"}
MAX_ROWS = 10_000


class IngestSummary(BaseModel):
    rows_total: int
    rows_with_txn_data: int
    transactions_ingested: int
    cohort_customer_ids: list[str]
    known_customer_ids: list[str]
    unknown_customer_ids: list[str]
    errors: list[str]


class CohortSweepRequest(BaseModel):
    customer_ids: list[str]


class CohortSweepResponse(BaseModel):
    requested: int
    swept: int
    skipped_unknown: list[str]
    decisions: list[DecisionOut]


def _normalise_header(name: str) -> str:
    return (name or "").strip().lower().replace(" ", "_")


def _parse_amount(raw: str) -> float | None:
    if raw is None or raw == "":
        return None
    cleaned = raw.replace(",", "").replace("₹", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_timestamp(raw: str) -> datetime:
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


@router.post("/transactions-csv", response_model=IngestSummary)
async def upload_transactions_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
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

    header_map = {_normalise_header(h): h for h in reader.fieldnames}
    if REQUIRED_COL not in header_map:
        raise HTTPException(400, f"CSV must contain a 'customer_id' column. Found: {list(header_map)}")

    cohort: set[str] = set()
    known: set[str] = set()
    unknown: set[str] = set()
    errors: list[str] = []
    rows_total = 0
    rows_with_txn = 0
    txns_added = 0

    customer_card_cache: dict[str, Card | None] = {}

    def card_for(customer_id: str) -> Card | None:
        if customer_id not in customer_card_cache:
            cust = db.query(Customer).filter(Customer.id == customer_id).first()
            customer_card_cache[customer_id] = cust.cards[0] if cust and cust.cards else None
        return customer_card_cache[customer_id]

    for idx, row in enumerate(reader, start=2):  # row 1 is header
        rows_total += 1
        if rows_total > MAX_ROWS:
            errors.append(f"Stopped at {MAX_ROWS} rows — upload smaller chunks")
            break

        cif = (row.get(header_map[REQUIRED_COL]) or "").strip()
        if not cif:
            errors.append(f"Row {idx}: empty customer_id")
            continue
        cohort.add(cif)

        card = card_for(cif)
        if card is None:
            unknown.add(cif)
            continue
        known.add(cif)

        amount_raw = row.get(header_map.get("amount", ""), "")
        amount = _parse_amount(amount_raw) if amount_raw else None
        has_txn_data = amount is not None

        if has_txn_data:
            rows_with_txn += 1
            tier_raw = (row.get(header_map.get("merchant_tier", ""), "") or "STANDARD").strip().upper()
            tier = "PREMIUM" if tier_raw == "PREMIUM" else "STANDARD"
            db.add(Transaction(
                id=f"TXN-UP-{uuid.uuid4().hex[:10].upper()}",
                card_id=card.id,
                amount=amount,
                merchant_category=(row.get(header_map.get("merchant_category", ""), "") or "UNKNOWN").strip().upper(),
                merchant_tier=tier,
                merchant_city=(row.get(header_map.get("merchant_city", ""), "") or "").strip() or None,
                timestamp=_parse_timestamp(row.get(header_map.get("timestamp", ""), "")),
            ))
            txns_added += 1

    db.add(AuditLog(
        entity_type="Ingest",
        entity_id=file.filename,
        action="CSV_UPLOAD",
        actor="dashboard_user",
        payload={
            "rows_total": rows_total,
            "transactions_ingested": txns_added,
            "cohort_size": len(cohort),
            "known": len(known),
            "unknown": len(unknown),
        },
    ))
    db.commit()

    return IngestSummary(
        rows_total=rows_total,
        rows_with_txn_data=rows_with_txn,
        transactions_ingested=txns_added,
        cohort_customer_ids=sorted(cohort),
        known_customer_ids=sorted(known),
        unknown_customer_ids=sorted(unknown),
        errors=errors,
    )


@router.post("/cohort-sweep", response_model=CohortSweepResponse)
def cohort_sweep(req: CohortSweepRequest, db: Session = Depends(get_db)):
    """Run the L3 decision engine across exactly the customer cohort supplied."""
    if not req.customer_ids:
        raise HTTPException(400, "customer_ids cannot be empty")

    decisions: list[Decision] = []
    skipped: list[str] = []
    for cif in req.customer_ids:
        customer = db.query(Customer).filter(Customer.id == cif).first()
        if not customer or not customer.cards:
            skipped.append(cif)
            continue
        card = customer.cards[0]
        evt = TriggerEvent(
            card_id=card.id,
            event_type="COHORT_SWEEP",
            payload={"sweep_at": datetime.utcnow().isoformat(), "uploaded": True},
        )
        db.add(evt)
        db.flush()
        dec = decision_engine.decide(db, customer_id=cif, trigger_type="COHORT_SWEEP")
        evt.decision_id = dec.id
        auto_execute_if_eligible(db, dec)
        decisions.append(dec)

    db.add(AuditLog(
        entity_type="Ingest",
        entity_id="cohort-sweep",
        action="COHORT_SWEEP_RUN",
        actor="dashboard_user",
        payload={
            "requested": len(req.customer_ids),
            "swept": len(decisions),
            "skipped_unknown": skipped,
        },
    ))
    db.commit()
    for d in decisions:
        db.refresh(d)
    return CohortSweepResponse(
        requested=len(req.customer_ids),
        swept=len(decisions),
        skipped_unknown=skipped,
        decisions=[DecisionOut.model_validate(d) for d in decisions],
    )


@router.get("/sample-csv")
def sample_csv():
    """Returns a small example dump so banks can see the expected format."""
    from fastapi.responses import PlainTextResponse
    lines = [
        "customer_id,timestamp,amount,merchant_category,merchant_tier,merchant_city",
        "CIF-1001,2026-06-20T14:23:11,4500.00,FINE_DINING,PREMIUM,Bengaluru",
        "CIF-1001,2026-06-21T09:15:00,1200.00,GROCERY,STANDARD,Bengaluru",
        "CIF-1003,2026-06-22T18:40:00,8800.00,TRAVEL_INTL,PREMIUM,Mumbai",
        "CIF-1007,2026-06-23T12:01:00,15500.00,LUXURY_RETAIL,PREMIUM,Delhi",
        "CIF-1011,2026-06-23T20:55:00,650.00,FUEL,STANDARD,Pune",
    ]
    return PlainTextResponse(
        "\n".join(lines) + "\n",
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="clr_sample_dump.csv"'},
    )
