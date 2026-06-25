# CLR — Credit Limit Revisioning Engine
## Full Product Architecture & Hyperface CCaaS Strategy
### Brainstorm Document — for Claude Code context

---

## 1. Product Overview

**Product name:** CLR (Credit Limit Revisioning Engine)
**Type:** AI-native B2B SaaS product
**Target buyers:** Indian banks (private sector, mid-tier, large urban co-operative banks, eventually PSU banks)
**Core value proposition:** Convert credit limit revision from a quarterly manual batch exercise into a continuous, event-driven, AI-personalized credit lifecycle management process.

**The problem today:**
Banks revise credit limits either annually in batch or only when a customer complaints. This creates two simultaneous failure modes:
- Good customers go underserved → low limits frustrate usage → competitor gains share
- Deteriorating customers get caught late → limits too high → NPA risk rises

**The CLR flip:** Continuous, event-driven, AI-personalized limit management with a real-time decisioning loop.

---

## 2. Full 7-Layer Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│              LAYER 1 — DATA INGESTION                            │
│  CIBIL/CRIF │ Account Aggregator │ CBS feed │ UPI/GST │ Telecom  │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│              LAYER 2 — AI / ML ENGINE (core brain)               │
│  Behavior model │ Income estimator │ Risk scorer │ GenAI explainer│
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│              LAYER 3 — DECISION ENGINE                           │
│  Policy rules │ Limit calculator │ Trigger engine │ HITL queue   │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│              LAYER 4 — CUSTOMER ENGAGEMENT                       │
│  GenAI nudge │ Consent flow │ Multi-channel │ Self-serve portal  │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│              LAYER 5 — BANK INTEGRATION                          │
│  REST/SFTP APIs │ CBS write-back │ Webhooks │ Finacle/Temenos     │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│              LAYER 6 — COMPLIANCE & GOVERNANCE                   │
│  RBI Master Dirs │ DPDP Act │ Audit trail │ Explainability logs  │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│              LAYER 7 — BANK ANALYTICS & ROI DASHBOARD           │
│  Funnel metrics │ Revenue uplift │ Default watch │ A/B cohorts   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Layer-by-Layer Breakdown

### Layer 1 — Data Ingestion

This is the product's moat. India has an unusually rich, consented data ecosystem.

| Data source | What it provides | Integration method |
|---|---|---|
| Account Aggregator (AA) framework | Real bank-account cash flow data with user consent | AA gateway API (Sahamati/Onemoney) |
| Bureau APIs | CIBIL, CRIF, Experian, Equifax — historical credit signals | Direct bureau API |
| CBS feed | Transaction history, payment record, existing limits | SFTP batch or CBS webhook |
| UPI transaction data | Spend patterns, merchant categories, frequency | NPCI / bank UPI data |
| GST-linked income | Declared income for self-employed, business owners | GST portal API (with consent) |
| Telecom signals | Payment behaviour proxy, stability indicators | Telco data partnerships |
| Device / app signals | Session frequency, app usage patterns | SDK embedded in card app |

**Key design principle:** Pre-built connectors for all data sources ship with the product. This is a 6-month head start over any bank building in-house.

---

### Layer 2 — AI / ML Engine

Four models working in tandem:

#### 2a. Behavioral Model
- Tracks spend velocity, repayment recency, utilisation trends over rolling 30/60/90 day windows
- Signals: spend moving up-market (lifestyle inflation → likely income growth), balance cycling (stress), card usage declining (competitor gaining share)
- Output: behavioral segment score (0–100), directional flag (improving / stable / deteriorating)

#### 2b. Income Estimator
- Triangulates: salary credits (CBS) + UPI inflows + AA cash flow data
- Refreshed every 30 days — stated income at origination goes stale, this is the critical differentiator
- For self-employed: uses GST turnover signals, UPI business receipts
- Output: estimated current net monthly income (with confidence interval)

#### 2c. Risk Scorer
- Produces: Probability of Default (PD), Loss Given Default (LGD), Exposure at Default (EAD)
- Inputs: bureau data + behavioral model output + income estimator output + CBS repayment history
- Model type: gradient boosted trees (XGBoost/LightGBM) with SHAP explainability
- Retraining cadence: monthly, with drift monitoring

#### 2d. GenAI Explainer Module
- Converts model outputs into plain-English reason codes
- Two audiences: (a) bank credit officer in HITL queue, (b) customer-facing notification
- Example output for officer: "Score improved 18 points. Primary drivers: 3 consecutive on-time payments, AA data shows 28% income growth, utilisation dropped from 72% to 41%."
- Example output for customer: "Your limit has been increased because your monthly income credits have grown consistently over the last 6 months and you've maintained a strong repayment record."
- Regulatory relevance: increasingly expected under RBI's fair lending guidance

**Technology stack suggestion:**
```
Behavioral model:   Python / PySpark on Kafka event stream
Income estimator:   Python / scikit-learn + AA API client
Risk scorer:        XGBoost + SHAP + MLflow for versioning
GenAI explainer:    LLM (Claude / GPT-4 class) with structured prompt templates
Model serving:      FastAPI + Redis cache for sub-100ms inference
Feature store:      Feast or Tecton for real-time feature serving
```

---

### Layer 3 — Decision Engine

#### 3a. Policy Rules (bank-configurable guardrails)
Banks configure hard constraints the AI cannot override. Examples:
- "Never upgrade a customer with >60 DPD in last 12 months"
- "Cap limit at 3× net monthly income"
- "Minimum 6 months at current limit before upgrade eligible"
- "Freeze limit for customers with bureau derogatory in last 90 days"

Rules engine: Drools or custom YAML-based rule DSL. Bank's credit policy team configures via dashboard — no engineering required.

#### 3b. Limit Calculator
Three possible decisions per customer review cycle:
- **Upgrade:** specific recommended limit (not just approve/reject — the model recommends an optimal target limit per customer that maximises revenue while holding PD below bank's threshold)
- **Downgrade:** for deteriorating risk signals
- **Freeze:** no change, flag for monitoring

Output format:
```json
{
  "customer_id": "CIF-XXXX",
  "current_limit": 100000,
  "recommended_limit": 150000,
  "decision": "UPGRADE",
  "confidence": 0.87,
  "pd_pre": 0.023,
  "pd_post_projected": 0.031,
  "income_estimate": 85000,
  "reason_codes": ["INCOME_GROWTH", "REPAYMENT_STREAK", "UTILIZATION_STABLE"],
  "explainer_text": "...",
  "trigger_type": "UTILIZATION_THRESHOLD",
  "hitl_required": false
}
```

#### 3c. Trigger Engine
Three trigger modes:

| Trigger type | Description | Example |
|---|---|---|
| Event-driven | Fires on specific transaction events | Customer hits 90% utilisation → immediate review |
| Periodic sweep | Scheduled batch over eligible customer pool | Monthly sweep of all active cardholders |
| Real-time income | Fires when income estimator detects step-change | Salary credit 30% above 6-month average |

#### 3d. Human-in-Loop (HITL) Maker-Checker
- Fully automated upgrades allowed up to a configurable threshold (e.g., ₹50,000 limit increase)
- Above threshold → goes to credit officer queue with full AI reasoning
- Maker-checker workflow for RBI compliance
- Target SLA: officer reviews within 24 hours, customer notified within 48 hours

---

### Layer 4 — Customer Engagement

#### 4a. Hyper-personalised Messaging
- GenAI drafts a unique notification per customer using their specific reason codes
- Not a template fill — genuinely personalised explanation
- Tone calibrated to customer's bureau segment (mass market vs. premium)

#### 4b. Consent Flow (DPDP-compliant)
- Pre-consent: "We'd like to review your credit limit. This uses your account data. Tap to allow."
- Post-decision: "Your limit has been revised. Here's why."
- Full consent log stored with timestamp, channel, and customer response
- Right to decline, right to erasure — all built in

#### 4c. Multi-channel Delivery
- Card app push notification (rich format with CTA)
- WhatsApp (for banks with WhatsApp Business API)
- SMS fallback
- Email for premium segment

#### 4d. Self-serve Portal
- Customer can see their new limit offer and optionally request a specific limit within the approved range
- Giving customers limited autonomy increases acceptance rates significantly
- Accept / decline tracked and fed back as signal to the model

#### 4e. A/B Testing Framework
- Test nudge copy, timing (morning vs evening), channel (push vs WhatsApp), offer framing
- Results feed back to engagement optimisation model
- Target metric: offer acceptance rate × incremental spend within 30 days

---

### Layer 5 — Bank Integration

Pre-built adapters (this is what gets the contract signed — banks won't buy anything requiring CBS replacement):

| System | Market | Integration type |
|---|---|---|
| Finacle (Infosys) | Dominant in PSU banks | REST API + SFTP |
| Temenos T24 | Several mid-tier private banks | REST API |
| Flexcube (Oracle) | ICICI, Kotak, Federal | SOAP/REST |
| BaNCS (TCS) | SBI, several co-operative banks | Batch + API |
| Generic SFTP | Any bank | Flat file exchange |

Write-back process on approval:
1. CLR API → Hyperface API (single call)
2. Hyperface → CBS update (limit field)
3. Hyperface → card network push (Visa/MC/RuPay authorisation limit update)
4. Hyperface → customer notification trigger
5. CLR records audit log with timestamps and response codes from all three systems

---

### Layer 6 — Compliance & Governance

| Requirement | Implementation |
|---|---|
| RBI Master Direction on Credit Cards | Policy guardrails in decision engine; HITL for large changes |
| DPDP Act (Digital Personal Data Protection) | Consent architecture, data residency, right to erasure |
| Fair Lending | AI model bias audit quarterly; proxy-discrimination checks |
| Model Explainability | SHAP values per decision; plain-English reason codes |
| Audit Trail | Immutable log: every decision, every input hash, every outcome |
| Model Drift Monitoring | Statistical drift alerts when score distribution shifts >5% |
| SOC 2 Type II / ISO 27001 | Product-level certifications; bank's legal team prerequisite |

---

### Layer 7 — Analytics & ROI Dashboard

Bank-facing dashboard that closes the ROI loop:

**Approval funnel metrics:**
- Customers eligible → reviewed → approved → notified → accepted
- Drop-off at each stage with drill-down

**Revenue uplift tracker:**
- Incremental spend from upgraded customers (vs control cohort)
- Interchange revenue delta
- Interest income delta (for revolving customers)

**Risk metrics:**
- Default rate delta: upgraded vs control
- PD accuracy: projected PD vs actual 90-day outcome
- Limit utilisation distribution post-revision

**Cohort A/B view:**
- Treatment vs control cohort performance
- Statistical significance calculator built in
- This is the renewal argument: "Here is the exact rupee amount of incremental revenue we generated this quarter."

---

## 4. Three AI Differentiators (Pitch-Ready)

### 4.1 Continuous Income Re-estimation
Using AA data to refresh income estimates every 30 days. No bank currently does this at scale. Approved income 3 years ago is not the customer's income today. A model that refreshes from live cash flow changes the accuracy of every limit decision.

### 4.2 Behavioral Segmentation Beyond Bureau
Bureau score = what happened historically. CLR behavioral model = what's happening now. Key signals:
- Spend moving up-market → likely income growth
- Balance cycling increase → financial stress
- Card usage declining → competitor gaining share
All invisible to a bureau.

### 4.3 Personalised Limit Recommendation, Not Just Approve/Reject
Instead of "upgrade to ₹2 lakh," the model recommends a specific optimal limit per customer that maximises revenue while holding PD below the bank's chosen threshold. Fundamentally different framing vs. standard credit review.

---

## 5. GTM Strategy for Indian Banks

### Target sequence
1. **Entry point:** Mid-sized private sector banks and large urban co-operative banks
   - Have the customer base to make numbers work (>500K active credit cards)
   - Under pressure to compete with HDFC/ICICI on credit products
   - Lack in-house tech to build CLR independently
2. **Expansion:** Large private sector banks (Axis, IndusInd, Federal)
3. **Long game:** PSU banks — longer sales cycle, larger contract

### Commercial model
- **Pilot structure:** 50,000-customer cohort, 3-month pilot
- **Pricing model:** Revenue-share (% of incremental interchange or interest income generated) — removes procurement objection, aligns incentives perfectly
- **Post-pilot:** Transition to SaaS licence with performance floor

### Regulatory tailwind
RBI's push on responsible credit (unsecured credit circular, late 2023) means banks actively need products that make limit revision processes more defensible — not just more aggressive. CLR is a compliance asset as much as a revenue tool.

---

## 6. What's Broken at the Bank's End — 5 Structural Gaps

```
BREAK 1 — CBS is batch, not real-time
┌─────────────────────────────────────────────────────────────┐
│ Finacle / Flexcube emits data in nightly dumps.             │
│ CLR AI model needs live transaction signals.                │
│ Customer's spend pattern from yesterday → invisible until   │
│ tomorrow morning's batch run.                               │
└─────────────────────────────────────────────────────────────┘

BREAK 2 — No real-time utilisation trigger
┌─────────────────────────────────────────────────────────────┐
│ Banks cannot fire a CLR review the moment a customer hits   │
│ 90% utilisation. The event happens but no system listens    │
│ to it and routes it into a credit decision workflow.        │
└─────────────────────────────────────────────────────────────┘

BREAK 3 — Limit change is a 3-system operation
┌─────────────────────────────────────────────────────────────┐
│ CBS update + card network push (Visa/MC/RuPay) +            │
│ customer notification = 3 separate teams, 3 separate APIs,  │
│ no atomic guarantee. Partial failures leave limits in an    │
│ inconsistent state between CBS and the network.             │
└─────────────────────────────────────────────────────────────┘

BREAK 4 — Limit and benefits are completely decoupled
┌─────────────────────────────────────────────────────────────┐
│ A LIT customer upgrading from ₹1L → ₹3L limit should auto- │
│ unlock a higher benefits tier. Banks have zero linkage      │
│ between the credit system and the benefits/rewards engine.  │
└─────────────────────────────────────────────────────────────┘

BREAK 5 — Comms layer is generic and bank-level
┌─────────────────────────────────────────────────────────────┐
│ Banks send a standard SMS for all card events.              │
│ No card-program-specific, contextual, or accept/decline     │
│ CTA-driven communication for a limit revision offer.        │
└─────────────────────────────────────────────────────────────┘

NET RESULT: Banks run CLR as a quarterly manual batch exercise
with a 6–8 week lag between signal and action.
```

---

## 7. Hyperface's Role as CCaaS Layer in CLR

Hyperface is a Credit Card as a Service (CCaaS) platform. It sits between the bank's CBS and the card network (Visa/MC/RuPay), owning: card program management, transaction processing, benefits/rewards orchestration, customer-facing notifications, and the onboarding journey.

**Core strategic insight:** A bank trying to run CLR without Hyperface hits a wall at the CBS — a batch, ledger-first system — at every layer that requires real-time operation. Hyperface is the real-time, event-driven card OS sitting in front of that CBS.

### Hyperface intervention across CLR layers

```
CLR Layer         │ What's broken at bank          │ Hyperface fix
──────────────────┼────────────────────────────────┼───────────────────────────────────
L1 — Data         │ CBS batch dumps, 12–24hr stale. │ Real-time authorisation event
                  │ Raw MCC codes, no enrichment.   │ stream. Enriched: category,
                  │                                 │ merchant, city, velocity.
──────────────────┼────────────────────────────────┼───────────────────────────────────
L2 — AI Engine    │ No structured spend signal.     │ Pre-enriched spend feed:
                  │ Behavioral model fed raw         │ category mix, merchant tier,
                  │ amounts only.                   │ velocity — AI-ready structure.
──────────────────┼────────────────────────────────┼───────────────────────────────────
L3 — Trigger      │ No utilisation webhook in CBS.  │ Authorisation webhooks. Fires
                  │ Triggers are periodic batch      │ on >80% utilisation, spend
                  │ jobs only.                      │ spike, or missed payment signal.
──────────────────┼────────────────────────────────┼───────────────────────────────────
L5 — Execution    │ 3-step operation: CBS write +   │ Single API call, atomic.
                  │ network push + notify.          │ HF owns CBS ↔ Visa/MC/RuPay
                  │ No atomic guarantee.            │ bridge. One call, consistent state.
──────────────────┼────────────────────────────────┼───────────────────────────────────
L4 — Engagement   │ Generic bank SMS. No card-      │ Card app notification layer.
                  │ program context. No accept/      │ Rich push with limit offer,
                  │ decline CTA.                    │ reason code, accept/decline CTA.
```

### The Unassailable Moat: Benefits Tier Coupling

```
┌──────────────────────────────────────────────────────────────────────┐
│  UNIQUE HYPERFACE CAPABILITY — not replicable by any other vendor    │
│                                                                      │
│  When CLR upgrades a LIT card from ₹1L → ₹3L limit:                │
│                                                                      │
│  Hyperface atomically upgrades the benefits tier too —               │
│  unlocking airport lounge access, higher cashback slabs,             │
│  or co-brand partner rewards via Poshvine / Zaggle.                  │
│                                                                      │
│  No bank can do this today. It requires owning both:                 │
│  (a) the limit execution layer, AND                                  │
│  (b) the benefits/rewards engine                                     │
│                                                                      │
│  Hyperface owns both. This is the unassailable moat.                 │
└──────────────────────────────────────────────────────────────────────┘
```

**Why this matters commercially:**
- A standard CLR vendor can revise the limit
- Only Hyperface can revise the limit AND the benefits tier in the same atomic operation
- This transforms CLR from a credit decision into a complete customer experience upgrade
- The bank's customers feel a step-change in their card — not just a bigger number, but new capabilities unlocked

### Hyperface Positioning Frame

> **"CLR without Hyperface is a dashboard. CLR with Hyperface is an operating system."**

The AI engine can produce perfect recommendations all day. Without the real-time data feed, event triggers, atomic execution, and benefits coupling that Hyperface provides, every recommendation still goes through a 6-week manual queue.

Hyperface is what converts the CLR product from a credit analytics tool into a live credit lifecycle management platform.

---

## 8. Product Bundling Strategy

**Option A — CLR as a standalone product (sold to any bank)**
- Bank must have separate CBS adapter work done
- Benefits coupling not available unless bank also onboards Hyperface
- Longer integration timeline

**Option B — CLR as a native Hyperface module (sold to existing Hyperface bank partners)**
- Zero integration work on data ingestion (HF already has the stream)
- Zero integration work on execution (HF already has the write-back)
- Benefits coupling available from day one
- Sales motion: upsell to existing AU, RazorpayX × YES Bank, and future programme partners
- Time to live: weeks, not months

**Recommended go-to-market priority:** Option B first — prove the product on existing HF bank relationships, generate ROI evidence, then sell Option A to non-HF banks (at a higher integration price point with longer onboarding).

---

## 9. API Contract Between CLR and Hyperface (Conceptual)

### Events Hyperface fires INTO CLR

```json
// Utilisation threshold event
{
  "event_type": "CARD_UTILIZATION_THRESHOLD",
  "card_id": "CARD-XXXX",
  "customer_id": "CIF-XXXX",
  "programme_id": "AU-LIT",
  "current_limit": 100000,
  "current_balance": 88000,
  "utilization_pct": 88.0,
  "timestamp": "2024-01-15T14:23:11Z"
}

// Spend spike event
{
  "event_type": "SPEND_SPIKE_DETECTED",
  "card_id": "CARD-XXXX",
  "customer_id": "CIF-XXXX",
  "rolling_30d_spend": 45000,
  "prior_30d_spend": 28000,
  "spike_pct": 60.7,
  "timestamp": "2024-01-15T14:23:11Z"
}

// Transaction enriched stream (continuous)
{
  "event_type": "TRANSACTION_ENRICHED",
  "card_id": "CARD-XXXX",
  "txn_id": "TXN-XXXX",
  "amount": 3500,
  "merchant_category": "FINE_DINING",
  "merchant_city": "Bengaluru",
  "merchant_tier": "PREMIUM",
  "timestamp": "2024-01-15T14:23:11Z"
}
```

### CLR fires BACK to Hyperface for execution

```json
// Limit upgrade instruction
{
  "instruction_type": "LIMIT_UPGRADE",
  "customer_id": "CIF-XXXX",
  "card_id": "CARD-XXXX",
  "programme_id": "AU-LIT",
  "current_limit": 100000,
  "new_limit": 150000,
  "benefits_tier_change": {
    "from": "SILVER",
    "to": "GOLD"
  },
  "notification_payload": {
    "channel": "PUSH",
    "headline": "Your credit limit has been upgraded",
    "body": "Based on your strong repayment record and income growth, your limit is now ₹1.5 lakh. You've also unlocked Gold benefits — including 2 lounge visits per quarter.",
    "cta": "View new benefits",
    "cta_url": "https://litcard.au.com/benefits"
  },
  "audit_reference": "CLR-DECISION-XXXX",
  "hitl_approved_by": null,
  "auto_approved": true
}
```

---

## 10. Open Questions / Next Steps

1. **AA integration depth:** What consent UX does Hyperface want to own vs. delegate to CLR's consent layer? Need to define API boundary.

2. **HITL queue ownership:** Does the bank's credit team use CLR's dashboard or Hyperface's? Or does CLR's HITL queue surface inside the bank's existing workflow tool?

3. **Model ownership:** Does CLR train a common model (federated, fine-tuned per bank) or does each bank's data stay fully siloed with separate model instances?

4. **Benefits tier configuration:** How does Hyperface expose the tier-change API? Is it a configuration-driven mapping (limit band → tier) or a freeform instruction from CLR?

5. **Regulatory sign-off process:** Which RBI Master Directions specifically govern automated credit limit revision? Need legal review of the HITL threshold.

6. **Pilot bank identification:** Which existing Hyperface bank partner is the best first CLR pilot candidate? (AU Small Finance Bank LIT programme is a strong candidate given existing relationship and programme maturity.)

---

*Document generated from product brainstorming session. All architecture decisions are conceptual and subject to technical feasibility review.*
*Context: Nishant Dash, Senior PM, Hyperface — Credit Card as a Service platform, India*
