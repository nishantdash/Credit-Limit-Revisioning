# CLR — Intent-Driven Credit Limit Revisioning Engine

A runnable prototype of the architecture in
[`Credit_Limit_Revisioning_Concept_Note.md`](./Credit_Limit_Revisioning_Concept_Note.md):
a real-time, **intent-driven** credit-limit revisioning engine that disambiguates
**growth vs distress vs seasonal**, emits a four-part decision (**direction,
magnitude, duration, confidence**), and orchestrates **consent-asymmetric**
offer/action pipelines on India's AA + DPDP + RBI rails.

It is delivered as a **configurable SaaS product** — one codebase, three
tenant archetypes (Bank / NBFC / SFB) selectable at runtime.

## What makes this different from a conventional engine

The orthodox Indian model asks *"how risky is this customer?"* and emits a single
new-limit number, one-directionally, on a quarterly batch. This engine asks
*"what is this customer trying to do right now, and why?"* and acts differently
for a customer who is growing versus one who is sliding.

| | Conventional | This engine |
|---|---|---|
| Orientation | Backward-looking (bureau, past repayment) | Forward-looking (live behaviour, intent) |
| Primary matrix | Risk × Utilisation | **Risk × Intent** (utilisation demoted to a modifier) |
| Output | One new-limit number | **direction + magnitude + duration + confidence** |
| Increases | Auto-applied | **Offer pipeline** — paused until OTP/MPIN consent |
| Decreases | Batch | **Action pipeline** — applied proactively with a buffer |
| Self-harm guard | None | **Anti-spiral guardrail** (velocity caps, leverage ceiling) |

## Architecture — the decision pipeline (§7.1)

```
knockout → 5 signal layers → risk/tier → intent → Risk×Intent matrix
        → capacity/buffer/inactivity formulas → anti-spiral guardrails
        → confidence gating → offer / action pipeline split → write-back
```

| Stage | Concept § | Module |
|---|---|---|
| Hard-knockout layer (fraud / legal / 30+ DPD bypass) | §2.6 | `engine/knockout.py` |
| Five signal layers (repayment trajectory, behavioural intent, stability, network, liquidity) | §2 | `engine/signals.py` |
| PD prior + dynamic risk tiers (1–4) | §3.1, §4.1 | `engine/risk.py` |
| **Intent disambiguation** (Growth / Distress / Seasonal / Neutral) | §3 | `engine/intent.py` |
| Risk × Intent matrix + utilisation modifier | §4.2–4.3 | `engine/matrix.py` |
| Capacity cap, decrease buffer, inactivity, **anti-spiral** guardrails | §5 | `engine/guardrails.py` |
| MSME double-gate + trade-credit early warning | §9 | `engine/msme.py` |
| Consent-asymmetric orchestration (offer vs action) | §6.1 | `engine/orchestration.py` |
| End-to-end decision orchestrator | §7.1 | `engine/decision.py` |
| Reason codes + officer/customer/consent copy | §6.2 | `engine/explainer.py` |
| Tenant configuration (Bank / NBFC / SFB presets) | §8 | `engine/config.py` |

The intent layer is an explicit **rules-over-features** design (the production
alternative is a tree/GBM model) because the problem is non-monotonic and
interaction-heavy: a velocity spike is *growth* only if inflow is stable **and**
category quality is rising; the same spike with rising min-due dependency and an
eroding buffer is *distress*. The conventional logistic PD model is retained as a
**prior**, not the decision-maker.

## The differentiators, wired in

1. **Intent disambiguation** — `intent.py` separates a +120% velocity spike into
   growth, distress, or seasonal from its *composition and context*, not the
   number alone.
2. **Risk × Intent matrix** — `matrix.py` fixes the cell the conventional model
   gets wrong: **Tier 3 × Growth**, where a subprime customer showing genuine
   upward mobility is held / cautiously, temporarily extended instead of auto-cut.
3. **Consent asymmetry** — increases are an **offer pipeline** (paused until
   OTP/MPIN); decreases are an **action pipeline** (applied with a 10% buffer +
   notify). `orchestration.py`.
4. **Anti-spiral guardrail** — `guardrails.py` caps the engine's own behaviour
   (frequency gate, per-customer leverage ceiling, portfolio increase-velocity
   cap, post-decrease cooldown) so a spend-maximising optimiser can't manufacture
   defaults two quarters out.
5. **Configurable SaaS** — `config.py` externalises every knob; switch Bank →
   NBFC at runtime and the same Tier-1 growth offer widens from +50% to +60%.
6. **MSME engine** — `msme.py` fuses promoter + business gates and weights
   trade-credit DPD as a primary, forward distress trigger.

## Run it

Two terminals. **Backend** (Python 3.11+; tested on 3.14):

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install --only-binary=:all: -r requirements.txt
.venv/bin/python -m app.seed             # seeds 15 archetypes across the matrix
.venv/bin/uvicorn app.main:app --port 8000
```

**Frontend** (Node 18+):

```bash
cd frontend
npm install
npm run dev                              # http://localhost:3000
```

### A useful walkthrough

1. **Triggers → Run full sweep** — the micro-review sweep scores all 15 customers
   and populates the book.
2. **Dashboard** — intent distribution, risk-tier spread, the pipeline split
   (offers awaiting consent vs decreases applied), and the anti-spiral gauge.
3. **Risk × Intent matrix** — see each customer land in a cell; the Tier 3 ×
   Growth showcase cell is highlighted.
4. **Offers** — approve a consent-gated increase via OTP/MPIN; the limit applies
   only on consent.
5. **Actions** — risk decreases already applied with their operational buffer.
6. **Customers → CIF-1009 (Meera)** — the Tier 3 × Growth case: five signal
   layers, the four-part decision, and a cautious temporary offer.
7. **Tenant config** — switch to NBFC, re-run the sweep, watch the same customers
   decided under a hotter policy.

### Seeded archetypes (one sweep, the whole matrix)

| Customer | Lands at | Demonstrates |
|---|---|---|
| Aarav, Diya, Ananya | Tier 1 × Growth | Aggressive consent-gated increase offers |
| Rohan | Tier 2 × Seasonal | **Temporary** auto-reverting offer |
| Kavya | Tier 2 × Neutral | Maintain |
| **Meera** | **Tier 3 × Growth** | **The showcase cell — cautious temp offer, not auto-cut** |
| Vikram, Sneha | Distress | Buffered decreases via the action pipeline |
| Patel Traders | MSME × Distress | Trade-credit double-gate early warning |
| Sharma Enterprises | MSME × Growth | Business-gate increase offer |
| Ishaan, Priya | Tier 4 × Knockout | 30+ DPD / fraud bypass to freeze/decrease |
| Rahul | Inactivity | Dormant limit right-sized (capital optimisation) |
| Aditya | Guardrail | Increase held by the frequency gate |

## Key API contracts

```http
GET  /config                 GET /config/presets        POST /config/activate   # tenant SaaS layer
POST /triggers/fire          POST /triggers/micro-review-sweep                   # §7.2 triggers
POST /webhooks/aa/event      GET /webhooks/cbs/outbound/{id}                     # AA rail + CBS write-back
GET  /offers                 POST /offers/{id}/consent   POST /offers/{id}/decline   # §6.1 offer pipeline
GET  /actions                                                                    # §6.1 action pipeline
GET  /review/queue           POST /review/{id}/approve   POST /review/{id}/reject    # confidence-gated HITL
GET  /analytics/funnel       GET /analytics/roi          GET /analytics/guardrails   # §7.3 / §5.4
GET  /decisions              GET /decisions/by-customer/{id}                      # four-part decisions
```

## What's intentionally a proxy

This is a demo of the **architecture and decision logic**, not a production system:

- **Signal layers & PD** use closed-form rule-based proxies in place of a feature
  store + PySpark/GBM serving. Swap behind the same `SignalBundle` / `RiskOutput`
  interfaces.
- **Explainer** uses deterministic templates; wire to an LLM with structured
  prompts for the customer-facing copy.
- **AA / CBS** are simulated by the webhook endpoints and a card-row write-back;
  real FIU/FIP and core-banking adapters slot in behind `orchestration.py`.
- **Champion-challenger** (§5.4) is represented by the portfolio velocity cap and
  guardrail telemetry, not a live cohort experiment loop.
- **Auth, RBAC, multi-tenant isolation, SOC 2** are out of scope for a prototype
  (the deployment model is single-tenant-per-install per §8.1).
