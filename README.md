# CLR — Credit Limit Revisioning Engine (prototype)

Runnable prototype of the 7-layer architecture described in
`CLR_ProductBrainstorm_ClaudeCode.md`. Demonstrates the full event → decision →
HITL → atomic write-back loop with seeded mock customers.

## What's in the box

| Layer | Brief | Prototype implementation |
|---|---|---|
| L1 — Data ingestion | AA / CBS / UPI / GST signals | `seed.py` loads 15 customer archetypes with income signals + 90 days of transactions; `/webhooks/hyperface/event` is the inbound Hyperface stream contract from §9; `/ingest/transactions-csv` accepts a bank CSV dump for piloting against a hand-picked customer cohort |
| L2 — AI engine | Behavioral, income, risk, GenAI explainer | `engine/behavioral.py`, `engine/income.py`, `engine/risk.py`, `engine/explainer.py` — closed-form proxies in place of PySpark / XGBoost / LLM so the demo is hermetic |
| L3 — Decision engine | Policy guardrails, limit calculator, triggers, HITL | `engine/policy.py`, `engine/decision.py`, `engine/trigger.py`, `routes/hitl.py` |
| L4 — Engagement | Personalised customer copy | Per-decision `explainer_text_customer` field; rendered in the dashboard |
| L5 — Bank integration | Atomic CBS + network + notification | `routes/hitl.py::_execute_decision` updates the card row + benefits tier + audit log in one transaction; `/webhooks/hyperface/outbound/{decision_id}` returns the §9 instruction payload |
| L6 — Compliance | Immutable audit log, reason codes, explainability | `AuditLog` model, `/analytics/audit-log`, SHAP-style feature contributions in `risk.py` |
| L7 — Analytics | Funnel, ROI, A/B placeholder | `/analytics/funnel`, `/analytics/roi`, dashboard at `/` |

The three pitch-ready differentiators from §4 of the brief are wired in:

1. **Continuous income re-estimation** — `income.py` triangulates CBS + AA + UPI + GST with confidence weighting.
2. **Behavioral segmentation beyond bureau** — `behavioral.py` produces a 0-100 score and IMPROVING/STABLE/DETERIORATING direction from 30/60-day spend windows, merchant-tier mix and utilisation.
3. **Personalised limit recommendation** — `decision._optimal_upgrade_limit` picks a per-customer target capped by income multiple and rounded to ₹5k, not a flat tier.

The Hyperface differentiator (**benefits tier coupling**, §7) is implemented in `engine/decision.py` — every approved upgrade carries an atomic `benefits_tier_change` in both the persisted Decision row and the outbound webhook payload.

## Run it

Two terminals. Backend (Python 3.11+ recommended; tested on 3.14):

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install --only-binary=:all: -r requirements.txt
.venv/bin/python -m app.seed          # seeds 15 customers + transactions
.venv/bin/uvicorn app.main:app --port 8000
```

Frontend (Node 18+):

```bash
cd frontend
npm install
npm run dev                            # http://localhost:3000
```

Open <http://localhost:3000>. Useful flow:

1. **Dashboard** — see the seeded funnel sit at 15 eligible / 0 reviewed.
2. **Trigger simulator** — click *Run periodic sweep on all 15 customers*. Funnel populates, several decisions land in HITL.
3. **HITL queue** — approve a couple of decisions; watch the dashboard executed count + ROI uplift update.
4. **Customers → CIF-1001 (Aarav Mehta)** — see the income signals, transaction stream, decision history with reason codes, and fire a follow-up event from the same page.
5. **Audit log** — every action above is in `/audit`.

## API contracts (mirror brainstorm §9)

```http
POST /webhooks/hyperface/event       # Hyperface → CLR (utilisation, spend spike, income step-change, enriched txn)
GET  /webhooks/hyperface/outbound/{decision_id}   # The LIMIT_UPGRADE payload CLR would POST to Hyperface
POST /triggers/fire                  # Manual trigger (dashboard simulator)
POST /triggers/periodic-sweep        # The §3c monthly batch
GET  /hitl/queue                     # PENDING decisions over the configurable threshold
POST /hitl/{id}/approve              # Maker-checker approval → atomic write-back
GET  /analytics/funnel               # L7 funnel metrics
GET  /analytics/roi                  # L7 ROI + risk
```

## What's intentionally not built

Production-grade pieces deferred to keep the prototype runnable in one command:

- **Real ML models** — `behavioral.py` and `risk.py` use closed-form rule-based proxies. Swap in PySpark/XGBoost serving via FastAPI per the brief's tech-stack suggestion.
- **Live LLM** — `explainer.py` uses deterministic templates. Wire to a Claude/GPT call with structured prompts when desired.
- **Real bank adapters** — Finacle/T24/Flexcube/BaNCS connectors per §5 are stubbed by the Card row update in `hitl_executor.py`.
- **Auth, RBAC, multi-tenancy, SOC 2 controls** — out of scope for a prototype.
- **Drift monitoring, A/B framework, federated training** — `/analytics/roi` has a single-cohort view; cohort/control plumbing would extend `Decision` with a cohort_id field.

This is a demo of the architecture and end-to-end flow, not a production system.
