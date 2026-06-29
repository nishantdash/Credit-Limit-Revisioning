"""Transaction-dump ingestion + cohort micro-review.

Accepts a CSV export from CBS for a specific customer cohort, attaches rows to
existing customers, then runs the intent engine over just that cohort so the
bank can pilot CLR against a hand-picked customer base.

Expected columns (case-insensitive; only customer_id is required):
  customer_id        required   CIF-XXXX
  timestamp          optional   ISO-8601; defaults to now
  amount             optional   float
  category_class     optional   ESSENTIAL | DISCRETIONARY | ASPIRATIONAL
  merchant_category  optional   free string, e.g. TRAVEL_INTL
  merchant_city      optional   free string
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
VALID_CATEGORIES = {"ESSENTIAL", "DISCRETIONARY", "ASPIRATIONAL"}


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
    header_map = {_norm(h): h for h in reader.fieldnames}
    if REQUIRED_COL not in header_map:
        raise HTTPException(400, f"CSV must contain a 'customer_id' column. Found: {list(header_map)}")

    cohort: set[str] = set()
    known: set[str] = set()
    unknown: set[str] = set()
    errors: list[str] = []
    rows_total = rows_with_txn = txns_added = 0
    card_cache: dict[str, Card | None] = {}

    def card_for(cif: str) -> Card | None:
        if cif not in card_cache:
            cust = db.query(Customer).filter(Customer.id == cif).first()
            card_cache[cif] = cust.cards[0] if cust and cust.cards else None
        return card_cache[cif]

    for idx, row in enumerate(reader, start=2):
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

        amount = _amount(row.get(header_map.get("amount", ""), ""))
        if amount is None:
            continue
        rows_with_txn += 1
        cat = (row.get(header_map.get("category_class", ""), "") or "ESSENTIAL").strip().upper()
        if cat not in VALID_CATEGORIES:
            cat = "ESSENTIAL"
        db.add(Transaction(
            id=f"TXN-UP-{uuid.uuid4().hex[:10].upper()}",
            card_id=card.id, amount=amount, category_class=cat,
            merchant_category=(row.get(header_map.get("merchant_category", ""), "") or "UNKNOWN").strip().upper(),
            merchant_city=(row.get(header_map.get("merchant_city", ""), "") or "").strip() or None,
            timestamp=_timestamp(row.get(header_map.get("timestamp", ""), "")),
        ))
        txns_added += 1

    db.add(AuditLog(entity_type="Ingest", entity_id=file.filename, action="CSV_UPLOAD",
                    actor="dashboard_user",
                    payload={"rows_total": rows_total, "transactions_ingested": txns_added,
                             "cohort_size": len(cohort), "known": len(known), "unknown": len(unknown)}))
    db.commit()
    return IngestSummary(
        rows_total=rows_total, rows_with_txn_data=rows_with_txn, transactions_ingested=txns_added,
        cohort_customer_ids=sorted(cohort), known_customer_ids=sorted(known),
        unknown_customer_ids=sorted(unknown), errors=errors,
    )


@router.post("/cohort-sweep", response_model=CohortSweepResponse)
def cohort_sweep(req: CohortSweepRequest, db: Session = Depends(get_db)):
    if not req.customer_ids:
        raise HTTPException(400, "customer_ids cannot be empty")
    config = cfg_mod.load_active(db)
    decisions: list[Decision] = []
    skipped: list[str] = []
    for cif in req.customer_ids:
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
                             "skipped_unknown": skipped}))
    db.commit()
    for d in decisions:
        db.refresh(d)
    return CohortSweepResponse(
        requested=len(req.customer_ids), swept=len(decisions), skipped_unknown=skipped,
        decisions=[DecisionOut.model_validate(d) for d in decisions],
    )


@router.get("/sample-csv")
def sample_csv():
    from fastapi.responses import PlainTextResponse
    lines = [
        "customer_id,timestamp,amount,category_class,merchant_category,merchant_city",
        "CIF-1001,2026-06-20T14:23:11,4500.00,ASPIRATIONAL,FINE_DINING,Bengaluru",
        "CIF-1001,2026-06-21T09:15:00,1200.00,ESSENTIAL,GROCERY,Bengaluru",
        "CIF-1003,2026-06-22T18:40:00,8800.00,ASPIRATIONAL,TRAVEL_INTL,Mumbai",
        "CIF-1007,2026-06-23T12:01:00,15500.00,ASPIRATIONAL,LUXURY_RETAIL,Delhi",
        "CIF-1011,2026-06-23T20:55:00,650.00,ESSENTIAL,FUEL,Pune",
    ]
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/csv",
                             headers={"Content-Disposition": 'attachment; filename="clr_sample_dump.csv"'})
