# Real-Time, Intent-Driven Credit Limit Revisioning

*A configurable SaaS decisioning engine for Indian Banks, NBFCs and Small Finance Banks*

**Document type:** Concept Note (not a PRD)  
**Prepared:** June 2026  
**Status:** For internal review and architecture alignment

---

# Executive Summary

Indian credit-limit management today is overwhelmingly **periodic, bureau-led and backward-looking**. Limits are reviewed in quarterly or half-yearly batches, driven by bureau scores and fixed income multipliers, and revised in one direction — upward when repayment looks good. This leaves three structural gaps: distress is detected a full reporting cycle late, growth-ready customers are starved of limit at the exact moment of intent, and undrawn limits sit on the balance sheet consuming capital.

This note proposes a **real-time, intent-driven Credit Limit Revisioning (CLR) engine**, delivered as a configurable SaaS product that runs **inside each lender’s own infrastructure**. It is designed natively for the Indian regulatory and data environment: the RBI requirement that limit **increases** require explicit customer consent while risk-driven **decreases** can be applied proactively; the DPDP Act 2023 and DPDP Rules 2025 governing behavioural data; and the Account Aggregator (AA) framework as the lawful, consent-based real-time data rail.

The engine’s differentiator over the conventional model is an **intent layer** that disambiguates why a customer’s behaviour is changing — growth, distress, or seasonal — and produces a four-part decision: **direction, magnitude, duration and confidence**. It is multi-tenant and configurable so that a large private bank, an NBFC, and a Small Finance Bank can each run their own risk appetite, parameters, and guardrails on the same codebase.

> **The one-line thesis**
> 
> Move credit-limit decisions from a backward-looking quarterly batch to a forward-looking, consent-respecting, real-time decision that can tell the difference between a customer who is growing and one who is sliding — and acts differently for each.

# 1. Why This, Why India, Why Now

## 1.1 The problem with the conventional Indian model

The orthodox approach — the same one most Indian issuers run today — is built on a small set of well-understood but slow signals. It is correct as far as it goes, but it is structurally incapable of the behaviour this product targets.

| **Dimension** | **Conventional model (today)** | **Intent-driven CLR (proposed)** |
| --- | --- | --- |
| Orientation | Backward-looking (bureau, past repayment) | Forward-looking (live behaviour, intent) |
| Cadence | Quarterly / half-yearly batch | Continuous + event-triggered |
| Inputs | Bureau score, income multiple, repayment | Intent, context, stability, liquidity, network |
| Direction | One-directional (raise on good repay) | Tri-directional: increase / decrease / hold |
| Timing | Customer-agnostic calendar | At the moment of need or stress |
| Output | A single new limit number | Direction + magnitude + duration + confidence |

Three concrete failures follow from this design. **Distress is detected late** — a borrower sliding toward default this week only shows up in the next bureau refresh or batch review. **Growth is missed** — a customer ready to spend more is not offered limit at the moment they would use it, so the spend (and the interchange and interest) goes to a competitor card. **Capital is wasted** — undrawn limits on dormant accounts tie up regulatory capital that could be redeployed.

## 1.2 Inspiration from China — adapted, not copied

China’s consumer-credit ecosystems (Sesame Credit, Tencent Credit, WeBank, MYbank) moved first on behavioural, real-time, graph-based limit management. The useful lessons are the **parameter philosophy** and the **intent disambiguation**, not the implementation. Several elements of the Chinese model — social-graph penalisation, opaque scoring, punitive “guilt by association” — are both reputationally and legally unacceptable in India and were themselves reined in. This product takes the forward-looking behavioural insight and rebuilds it on India’s consent-first rails.

> **What we borrow vs. what we leave**
> 
> **Borrow:** behavioural and intent signals as primary inputs; real-time event-driven revisioning; the idea that the same spend spike means different things in different contexts; ability + stability + liquidity as distinct pillars.
> 
> **Leave:** social-graph penalisation, punitive network scoring, opaque/unexplainable decisions, and any use of behavioural data without explicit, purpose-bound consent.

## 1.3 Why the Indian market is ready now

- **Real-time data rail exists.** The Account Aggregator framework provides consent-based, encrypted, machine-readable financial data in seconds. As of December 2025 the ecosystem reported on the order of 2.6 billion enabled accounts and hundreds of millions of active users, with 400+ registered FIUs — the rail this engine consumes is now mainstream, not experimental.
- **Regulation has drawn clear lines.** RBI’s credit-card rules make the consent boundary explicit: increases need the customer’s active approval; risk-driven decreases can be applied to protect both parties. This is not a constraint to fight — it is the exact shape the product is designed around.
- **Card and credit base is large and stressed in pockets.** With the active credit-card base past 100 million and rising revolving balances, the cost of late distress detection and the upside of well-timed growth offers are both material.
- **DPDP gives a stable compliance target.** With the DPDP Rules notified in November 2025, lenders finally have a concrete data-protection regime to build to, rather than a moving target.

# 2. Parameter Architecture: The Five Signal Layers

The engine ingests parameters in five layers. Layers 1–3 exist in the conventional model and are retained; Layers 4–5 are the intent-driven additions that make real-time, forward-looking decisions possible. Each parameter carries a **weight** that is tenant-configurable, so a conservative SFB and an aggressive NBFC can run the same engine with different emphases.

## 2.1 Layer 1 — Repayment & Credit History (foundational)

Retained from the conventional model, but made **trajectory-sensitive**: the engine reads trends and slopes, not just levels. A customer at a given payment ratio that is falling is a very different risk from the same ratio rising.

| **Parameter** | **Definition** | **Intent relevance** |
| --- | --- | --- |
| Payment Quality Ratio (PQR) | Total paid ÷ total statement balance, 3-month rolling | Level + **slope** of PQR |
| Utilization trend | Current balance ÷ limit, with direction | Rising vs. falling utilisation |
| Min-due dependency slope | Trend in reliance on paying only minimum due | Early distress signal |
| DPD history | Entries into 1–29 / 30+ days past due | Risk + knockout |
| Account vintage | Age of the credit relationship | Confidence weighting |

## 2.2 Layer 2 — Behavioural & Transactional Intent (the differentiator)

This is the layer the conventional model lacks. Spend is decomposed rather than treated as a single velocity number, because **the same spike means opposite things** depending on its composition and context.

| **Parameter** | **Definition** | **Intent relevance** |
| --- | --- | --- |
| Category-mix vector | Distribution of spend across essential / discretionary / aspirational | Direction of lifestyle change |
| Category-mix drift | Change in that vector over time | Growth vs. distress |
| Velocity (decomposed) | Acceleration split by discretionary vs. essential | Confident growth vs. plugging a hole |
| Merchant-quality trend | Quality/consistency of merchants over time | Stability of spend |
| Recurrence / stickiness | Subscriptions, recurring mandates | Embeddedness, predictability |
| Declined-transaction events | High-value declines against limit | Strong real-time demand signal |

> **The core insight, stated plainly**
> 
> A doubling of spend velocity is meaningless on its own. Velocity rising **into discretionary and aspirational categories, with stable inflow** is growth. The same velocity rising **with min-due dependency climbing and inflow turning erratic** is distress. The conventional engine sees one number and cannot tell them apart. The intent engine is built precisely to separate them.

## 2.3 Layer 3 — Stability & Fulfilment (ability + stability)

China’s “ability and stability” pillar. In the Indian build this is sourced cleanly and lawfully through the Account Aggregator rail, which is the single most important real-time predictor and is currently wasted by most engines.

| **Parameter** | **Definition and why it matters** |
| --- | --- |
| Inflow regularity | Consistency and predictability of credits (salary / business inflow). The strongest real-time stability signal. |
| Salary-cycle phase | Where in the pay cycle the customer is — reframes a utilisation spike as routine vs. abnormal. |
| Inflow / outflow buffer | Cash cushion between money in and money out; a live liquidity-state read. |
| Identity / device stability | Address, device, SIM continuity — positive-only signals, never punitive. |

## 2.4 Layer 4 — Network signals (positive-only, optional)

Tencent-style ecosystem embeddedness, included **only as a positive enhancer and only where the tenant opts in**. To avoid the fairness and regulatory failures of the Chinese social-graph model, the engine **never penalises** a customer for their counterparties. Network signals can lift confidence in a growth decision; they can never, by themselves, drive a decrease.

- Quality and regularity of payee/payer relationships (e.g. consistent salary from a verifiable employer).
- Counterparty regularity for MSMEs (stable buyer/supplier settlement patterns).

> **Hard rule**
> 
> Network signals are **additive and positive-only**. No “guilt by association.” A customer is never downgraded because of who they transact with. This is a non-negotiable design constraint, both for DPDP fairness and for reputational safety.

## 2.5 Layer 5 — Real-time context & liquidity state

- Current cash-flow position and buffer (from AA), giving a live affordability read at decision time.
- Seasonal / festive context — enables **temporary, auto-reverting** limit changes rather than permanent leverage.
- Event context — a salary credit, a large pre-authorised spend, or a missed obligation elsewhere becomes a trigger, not just a logged fact.

## 2.6 Hard-knockout layer (evaluated first, bypasses scoring)

Before any scoring runs, binary blocks are checked. Any hit forces a freeze/decrease path and skips the intent model entirely.

- Active fraud or identity-fraud flags.
- Legal block or bankruptcy/insolvency status.
- Active 30+ DPD.

# 3. The Intent Disambiguation Engine

This is the heart of the product and the part that has no equivalent in the conventional documents. The engine answers a question the orthodox model never asks: **not “how risky is this customer?” but “what is this customer trying to do right now, and why?”**

## 3.1 Why logistic regression alone cannot do this

A single logistic/scorecard model collapses everything onto one monotonic axis: higher score, higher risk. But the hardest problem here is **non-monotonic and interaction-heavy** — velocity is good *only if* inflow is stable *and* category quality is rising. That conditional structure is not a weighted sum. The intent layer therefore uses tree-based / gradient-boosted models or an explicit rules-over-features design, while the conventional logistic PD model is retained as a **prior**, not as the decision-maker.

## 3.2 The three intents

| **Intent** | **Signature** | **Engine response** |
| --- | --- | --- |
| Growth | High velocity + rising category quality + stable inflow + healthy buffer | Increase (offer, consent-gated), permanent |
| Distress | Velocity + rising min-due dependency + erratic inflow + shrinking buffer | Decrease / hold + intervene |
| Seasonal | Utilisation spike + festive/seasonal context + prepayment behaviour | **Temporary** increase, auto-reverts |

## 3.3 The four-part output

Unlike the conventional engine, which emits a single new-limit number, the intent engine emits a **structured decision object**:

| **Field** | **Meaning** |
| --- | --- |
| direction | increase / decrease / maintain |
| magnitude | size of the change, bounded by capacity caps and tenant matrix |
| duration | permanent or temporary (with an auto-revert date for seasonal) |
| confidence | model certainty — low confidence routes to nudge-and-observe or manual review rather than auto-apply |

> **Worked disambiguation**
> 
> **Input A:** spend velocity +120%, discretionary share rising, salary credited on time for 6 months, buffer healthy → {increase, +20%, permanent, high} → push a consent-gated increase offer.
> 
> **Input B:** spend velocity +120%, min-due dependency rising 3 months straight, last two salary credits irregular, buffer shrinking → {decrease, −15%, permanent, high} → apply risk decrease with buffer, trigger outreach.
> 
> **Input C:** spend velocity +120%, concentrated in travel/retail in festive window, customer historically prepays → {increase, +15%, temporary 60 days, medium} → offer temporary bump that auto-reverts.

# 4. Risk Tiers and the Decision Matrix

## 4.1 Dynamic risk tiers

Accounts are bucketed into four tiers by composite performance, evaluated continuously rather than at period-end. The hard-knockout layer can place an account in Tier 4 instantly, bypassing scoring.

| **Tier** | **Target PD** | **Profile** |
| --- | --- | --- |
| Tier 1 — Elite | < 0.5% | Transactors who pay in full; top-bracket bureau, PQR ≥ 0.95, no DPD, no late fees. |
| Tier 2 — Prime | 0.5% – 3.0% | Stable revolvers who carry a balance occasionally but pay well above minimum; stable utilisation. |
| Tier 3 — Subprime / Watch | 3.0% – 10.0% | Credit stress or heavy min-due reliance; rapid bureau drop, low PQR, or frequent 1–29 DPD. |
| Tier 4 — Critical | > 10.0% | Severe distress, fraud, or legal status; active 30+ DPD. Evaluated via binary flags, bypassing scoring. |

## 4.2 The reframed matrix: Risk × Intent

The conventional document’s matrix is **Risk × Utilization**. This product’s primary matrix is **Risk × Intent**, with utilisation demoted to a modifier (it is a state input, not a decision axis). This is the single most important structural change, and it fixes the cell the conventional model gets wrong.

|   | **Growth intent** | **Neutral / maintenance** | **Distress intent** |
| --- | --- | --- | --- |
| Tier 1 Elite | Aggressive ↑ instant, permanent | Maintain | Hold + observe (likely seasonal → offer temporary ↑) |
| Tier 2 Prime | Moderate ↑, step-up | Maintain | Hold + soft engage; freeze velocity |
| Tier 3 Subprime | **Cautious temporary ↑ or hold** (do not auto-cut a growing customer) | ↓ slowly | ↓ sharply + restructure offer |
| Tier 4 Critical | Freeze regardless of intent | Freeze | Collapse to obligation |

> **The cell the conventional model gets wrong**
> 
> Tier 3 × Growth. The orthodox engine cuts or freezes any subprime account. But a subprime customer whose behaviour shows genuine upward mobility — rising category quality, stabilising inflow — is a future Tier 2 customer. Auto-cutting them hands them to a competitor. The intent matrix holds or cautiously, temporarily extends instead.

## 4.3 Utilization as a modifier

Utilisation still matters — it scales magnitude and gates certain actions — but it no longer defines the decision. For a growth-intent Tier 1 customer, high utilisation argues for a larger increase; for a distress-intent Tier 3 customer, high utilisation argues for a gentler decrease (to avoid triggering declines). The conventional multiplier bands are retained as **magnitude inputs**, not as the matrix itself.

| **Tier** | **High util (>60%)** | **Moderate (15–60%)** | **Low (<15%)** |
| --- | --- | --- | --- |
| Tier 1 Elite | +30% to +50% | +15% to +25% | 0% (capital lock) |
| Tier 2 Prime | +15% to +20% | 0% maintain | 0% maintain |
| Tier 3 Subprime | 0% maintain | −20% to −40% | −50% to −70% |
| Tier 4 Critical | Freeze / collapse | Freeze / collapse | Freeze / collapse to zero |

These bands are **defaults**. Every band is tenant-configurable, and every increase is additionally bounded by the capacity caps in Section 5 and gated by consent in Section 6.

# 5. Decision Formulas and Guardrails

The matrix produces a target direction and magnitude band. Three formulas then bound it so the engine cannot manufacture the very risk it exists to control. These adapt the conventional model’s capacity logic and add the anti-spiral guardrail the orthodox design lacks.

## 5.1 Proactive increase — capacity-cap model

Every calculated increase is strictly bounded by the customer’s estimated financial capacity, so a growth signal can never push a customer past affordability.

```
Δ = min( Matrix_Max ,  [ (Est_Income × Max_DTI) − External_Debt ] ÷ CL_current  − 1 )
```

Estimated income and external debt obligations are sourced in real time via the Account Aggregator rail, which is what makes this a live affordability check rather than a stale one.

## 5.2 Risk-based decrease — exposure minimisation with buffer

Decreases are applied without triggering immediate over-limit fees or declines, by holding a 10% operational buffer above current outstanding.

```
CL_new = max( Outstanding × 1.10 ,  CL_current × (1 − Decrease_Mult) )
```

Because RBI permits risk-driven decreases to be applied proactively (unlike increases), this path can execute without waiting for consent — but it always notifies the customer and always preserves the buffer.

## 5.3 Inactivity decrease — capital optimisation

Dormant undrawn limits are right-sized to free regulatory capital, anchored to the customer’s own recent peak so the change is never punitive.

```
CL_new = Peak_Utilization_last_12m × 1.5     (when util < 5% for > 12 months)
```

## 5.4 The anti-spiral guardrail (new — not in the conventional model)

A self-optimising engine tuned to “increase spend/usage” can learn to manufacture over-leverage that surfaces as defaults two quarters later — after the KPI dashboard has already rewarded it. This is the blind spot a cohort/PD framework has by construction, because it measures damage a full cycle after the engine caused it. The engine therefore caps its own behaviour:

- **System-level increase-velocity cap:** a ceiling on how much aggregate limit the engine can extend across the portfolio per unit time, independent of individual eligibility.
- **Per-customer leverage ceiling:** cumulative increases over a rolling window are bounded regardless of how many positive signals fire.
- **Champion-challenger containment:** challenger strategies that improve the spend KPI but degrade forward delinquency are auto-rolled-back, with delinquency measured on a lagged cohort, not on same-period spend.

> **Why this matters**
> 
> The product has two goals that can fight each other: increase spend, and control defaults. Without an explicit anti-spiral guardrail, an optimiser will quietly sacrifice the second to win the first, and the lag will hide it until it is expensive. This guardrail is what keeps the engine honest.

# 6. Regulatory and Consent Design (India-Specific)

This product is designed around Indian regulation, not retrofitted to it. Three regimes shape the design directly: RBI credit-card / lending rules, the DPDP Act 2023 with DPDP Rules 2025, and the Account Aggregator framework. The single most important architectural consequence is the **consent asymmetry**.

## 6.1 The consent asymmetry (the design pivot)

| **Action** | **RBI position** | **Engine behaviour** |
| --- | --- | --- |
| Limit increase | Requires **explicit** customer consent (digital/OTP/written). Silence ≠ approval. Customer must be notified and able to accept/reject. | Engine computes and **offers**; change stays paused until the customer actively approves via OTP/MPIN. Never auto-applied. |
| Limit decrease (risk) | Permitted proactively for risk control; customer must be informed. | Engine **applies** with operational buffer and notifies; no pre-approval required. |
| Over-limit | Only with opt-in; charges on un-consented over-limit must be reversed. | Engine never relies on silent over-limit; respects opt-in state. |

> **Design consequence**
> 
> Increases are an **offer pipeline**, decreases are an **action pipeline**. The entire orchestration layer is built on this split. An engine that tries to auto-apply increases is not merely sub-optimal in India — it is non-compliant.

## 6.2 DPDP Act 2023 + Rules 2025 obligations

Behavioural and intent data are personal data. The DPDP Rules (notified November 2025, phased compliance) make the lender a Data Fiduciary with concrete duties the engine must support natively:

- **Purpose-bound, itemised consent:** behavioural data is processed only for the stated CLR purpose, with consent that is free, specific, informed and revocable as easily as it was given.
- **Data minimisation & retention limits:** only what the decision needs, retained only as long as needed, with purpose-based retention timelines.
- **Right to access, correct, erase, withdraw:** the engine must expose and honour these, including downstream erasure at processors.
- **Explainability / reason codes:** every revision carries a reason code — required both for RBI and for customer trust; large fiduciaries face algorithmic-fairness and DPIA obligations.
- **Breach posture:** breach notification duties (72-hour reporting to the Board) inform the security design in Section 7.

## 6.3 Account Aggregator as the lawful data rail

The engine does not screen-scrape or rely on PDF uploads. It consumes data through the AA framework, where the lender is a registered **FIU**, the bank/NBFC holding data is an **FIP**, and a licensed **AA** is the blind, data-minimising consent pipe that can neither read nor store the data.

- Time-bound, purpose-specified consent (e.g. “limit review,” not “general access”) with a defined fetch frequency.
- ReBIT-standardised, machine-readable data — one parser works across all FIPs.
- Instant revocation: when a customer revokes, fetches stop immediately and the engine degrades gracefully to internal-only signals.

> **Consent as a growth lever, not just a hurdle**
> 
> Framing matters. “Authorise data transfer” converts poorly; “Share your income securely to unlock a higher limit / lower rate” ties the consent directly to the reward. The product surfaces consent at the moment of value, which both improves conversion and satisfies the informed-consent standard.

# 7. Real-Time Architecture

The engine is event-driven and decoupled — no end-of-day batch dependency. The conventional document’s three-layer backbone (ingestion → analytics → orchestration) is the right shape and is retained; the intent classifier is inserted between analytics and the matrix, and a consent/guardrail layer wraps execution.

## 7.1 Logical flow

| **Stage** | **Function** |
| --- | --- |
| Event & ingestion (L1) | Streaming platform (e.g. Kafka) captures triggers — salary credit, payment clear, transaction decline, AA data push. Fast cache (e.g. Redis) holds a rolling 90-day window of transaction and utilisation metrics. |
| Analytics & risk (L2) | Feature store serves internal + AA-derived features; lightweight bureau/micro-bureau calls validate macro risk; PD prior computed. |
| Intent classifier (new) | Tree/GBM or rules-over-features model fuses risk + intent features into {direction, magnitude, duration, confidence}. |
| Matrix + capacity caps | Risk × Intent lookup, bounded by capacity-cap and decrease-buffer formulas. |
| Guardrail layer | Regulatory caps, frequency gates, anti-spiral velocity caps, cooldowns, reversibility flags. |
| Orchestration (L3) | Splits into offer pipeline (increase → consent push, paused until OTP/MPIN) vs. action pipeline (decrease → apply + notify). Writes to core banking. |

## 7.2 Trigger types

- **Event-driven:** salary credit, large pre-auth, declined high-value transaction, missed obligation detected via AA.
- **Threshold-driven:** utilisation crosses a configured band; min-due dependency slope crosses a limit.
- **Scheduled micro-reviews:** lightweight continuous re-scoring, replacing the quarterly batch.

## 7.3 Continuous optimisation

A champion-challenger loop tests alternate multipliers on a small, eligible cohort to benchmark risk tolerance and update matrix thresholds — contained by the anti-spiral guardrail (Section 5.4) so challengers that win on spend but lose on lagged delinquency are rolled back automatically.

# 8. SaaS Product Design on Bank Infrastructure

The requirement is a product that behaves as SaaS — configurable per institution — yet runs **inside each lender’s own infrastructure**. In Indian financial-services reality, customer financial data generally cannot leave the bank’s controlled environment, so this is a **single-tenant deployment, multi-tenant product** model: one codebase, deployed per tenant, with all configuration externalised.

## 8.1 Deployment model

| **Aspect** | **Approach** |
| --- | --- |
| Hosting | Deployed within the bank/NBFC/SFB’s own VPC or data centre; data never leaves the tenant boundary. |
| Delivery | Containerised (e.g. Kubernetes/Helm), so the same artefact installs identically across tenants. |
| Isolation | One logical tenant per deployment; no cross-tenant data path exists by construction. |
| Updates | Versioned releases; tenant controls upgrade timing; configuration migrates forward. |
| Core-banking integration | Adapter layer abstracts the core banking system so the engine is CBS-agnostic. |

## 8.2 What is configurable per tenant

Everything that encodes risk appetite or policy is externalised into a tenant configuration, so a conservative SFB and an aggressive NBFC run the same engine very differently without code changes.

- **Parameter weights** across all five signal layers, and which optional layers (e.g. network) are enabled.
- **Risk-tier thresholds** and target PD bands.
- **Matrix multiplier bands** (the increase/decrease magnitudes per cell).
- **Capacity caps:** Max-DTI, income-estimation method, decrease buffer %.
- **Guardrails:** frequency gates (e.g. one increase per 180 days), cooldowns, anti-spiral velocity caps, per-customer leverage ceilings.
- **Consent flows & copy:** OTP/MPIN channel, notification templates, AA consent scope and fetch frequency.
- **Confidence thresholds:** where auto-offer ends and manual review begins.
- **Auto-apply vs. offer-only** posture for each action type (within RBI limits — increases always remain consent-gated).

## 8.3 Tenant tiers — Bank vs. NBFC vs. SFB

| **Dimension** | **Large Bank** | **NBFC** | **Small Finance Bank** |
| --- | --- | --- | --- |
| Typical appetite | Balanced, capital-optimising | Growth-led, higher yield | Inclusion-led, thin-file heavy |
| Data richness | Often first-party + AA | AA-reliant | AA + alternative data |
| Emphasis | Capital lock + Tier-1 growth | Aggressive Tier-2 growth | Stability + cautious Tier-3 mobility |
| Default config | Tight guardrails, lower velocity cap | Wider bands, higher cap | Conservative caps, strong distress watch |

> **First-party data fork (the decision that shapes the intent layer)**
> 
> Whether a tenant has first-party ecosystem/behavioural data or is bank/AA-data-only determines how rich and pre-emptive the intent classifier can be. The product is built to work in **both** modes: a full pre-emptive intent layer where first-party signals exist, and an intent layer reconstructed from transaction + AA exhaust where they do not. The default deployment assumes AA-only and treats first-party data as an enhancement, so the product is viable for every tenant from day one.

# 9. Retail and MSME: Two Engines, One Platform

Salaried individuals and businesses have fundamentally different risk structures, so the platform runs **two parallel decisioning engines** sharing the same architecture and guardrails. Critically, the intent signals themselves invert between the two.

| **Attribute** | **Retail (salaried / individual)** | **MSME / business** |
| --- | --- | --- |
| Primary income | Stable, predictable salary inflow | Volatile, seasonal business cash flow |
| Key affordability metric | DTI, inflow regularity | DSCR, current/quick ratio, leverage |
| Earliest distress signal | Min-due dependency slope, irregular salary | **DPD on supplier invoices** (trade credit) — fires before bank distress |
| Intent proxy | Category-mix drift, spend velocity | Working-capital utilisation, trade-settlement regularity |
| Model structure | Fully automated | Hybrid: scorecard + expert judgment + double-gate |

> **The MSME early-warning edge**
> 
> A business signals distress to its **vendors** before it signals distress to its bank. Trade-credit DPD — available via GST/trade-bureau data — is a forward, real-time, intent-grade signal with no retail equivalent. The MSME engine therefore weights trade-credit deterioration as a **primary** trigger, not a secondary one. This is a genuine information advantage the conventional retail-only model leaves on the table.

## 9.1 The MSME double-gate

For MSMEs the promoter’s personal finances and the business are intertwined, so the engine scores both and fuses them:

```
Final_Grade  =  f( Promoter_Personal_Score ,  Business_Financial_&_Trade_Score )
```

A specific, nameable distress pattern the gates catch only together: the promoter’s **personal** spend velocity spikes while the **business** working-capital line maxes out. Neither gate alone sees it; the fused view does.

# 10. Assumptions and Implications

## 10.1 Key assumptions

| **Assumption** | **Implication if it does not hold** |
| --- | --- |
| Customer grants AA consent for live data | Engine degrades to internal-only signals; intent layer weaker but still functional |
| Core banking exposes a real-time limit-update API | Falls back to near-real-time queued updates; latency rises |
| Tenant accepts consent-gated increases (RBI) | Non-negotiable — product is built on this; no auto-increase path exists |
| First-party behavioural data may be absent | Default AA-only mode assumed; first-party treated as enhancement |
| DPDP phased compliance timeline holds | Build to the earlier prudent baseline; configuration absorbs date shifts |
| Bureau / trade-bureau data available for MSME | MSME engine needs trade data; absence reverts it to financials-only scoring |

## 10.2 Broader implications

- **Operating-model shift:** from a quarterly credit-policy committee cadence to continuous, policy-as-configuration governance. Risk teams own the config, not a batch job.
- **Explainability is load-bearing:** reason codes are not a nicety; they are required for RBI, DPDP, and customer dispute handling. Model choices that sacrifice explainability are constrained.
- **Customer-experience risk:** yo-yo limits erode trust. Cooldowns and reversibility flags exist specifically to prevent this.
- **Capital impact is real but bounded:** inactivity right-sizing frees capital, but must be paced so it does not read as a mass de-risking event.

# 11. Key Risks and Mitigations

| **Risk** | **Description** | **Mitigation** |
| --- | --- | --- |
| Self-induced over-leverage | Optimiser manufactures defaults to win the spend KPI | Anti-spiral velocity caps; lagged-cohort delinquency in champion-challenger |
| Intent misclassification | Distress read as growth (or vice-versa) | Confidence gating; low-confidence routes to observe/manual; human-in-loop for edge cases |
| Consent / regulatory breach | Auto-applying an increase; mis-scoped data use | Offer-pipeline split; purpose-bound AA consent; reason codes; DPIA |
| Fairness / bias | Network or alt-data penalises unfairly | Positive-only network signals; no guilt-by-association; fairness assessment |
| Data-quality drift | Feature/PSI drift degrades decisions | Monitoring, drift alerts, periodic re-validation |
| Reputational (yo-yo limits) | Frequent reversals erode trust | Cooldowns, frequency gates, reversibility flags, temporary-limit auto-revert |

# 12. Phased Build Approach

A pragmatic sequence that delivers compliant value early and adds intelligence in layers. Each phase is independently shippable.

| **Phase** | **Scope** | **Outcome** |
| --- | --- | --- |
| Phase 1 Foundation | Event backbone (Kafka/Redis), feature store, risk tiers, Risk×Utilization matrix, decrease + capacity formulas, AA-FIU integration, consent split, reason codes | Compliant real-time decreases + capital optimisation; offer-gated basic increases |
| Phase 2 Intent layer | Intent classifier, Risk×Intent matrix, four-part output, temporary/auto-revert limits, anti-spiral guardrail | Growth/distress/seasonal disambiguation; the core differentiator live |
| Phase 3 MSME engine | Double-gate scorecard, trade-credit/GST signals, DSCR-based capacity | Parallel MSME decisioning with trade-credit early warning |
| Phase 4 Optimisation | Champion-challenger with lagged-cohort containment, first-party data enrichment, per-tenant tuning | Self-improving thresholds within safe bounds |

## Closing note

The foundations — PD modelling, scorecards, risk tiers, capacity caps — are orthodox and well-understood. What makes this product is the **intent layer, the consent-asymmetric orchestration, the temporary-limit mechanism, and the anti-spiral guardrail**, all built natively on India’s AA + DPDP + RBI rails and delivered as configurable software that runs inside each lender’s own walls. That combination is what the conventional Indian model cannot do, and what the Indian market is now — finally — equipped to support.
