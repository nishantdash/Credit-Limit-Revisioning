"""Seed the DB with archetypes that exercise the full intent engine.

The roster is hand-built so a single micro-review sweep produces a realistic
spread across the Risk × Intent matrix:

  GROWTH   → consent-gated increase offers (incl. the Tier 3 × Growth showcase)
  DISTRESS → buffered decreases applied via the action pipeline
  SEASONAL → temporary, auto-reverting increase offers
  NEUTRAL  → maintain / capital-lock
  KNOCKOUT → fraud / 30+ DPD bypass to a freeze/decrease
  INACTIVITY, FREQUENCY_GATE → guardrail demonstrations
  MSME     → trade-credit double-gate early warning
"""
import random
import uuid
from datetime import datetime, timedelta

from .db import Base, SessionLocal, engine
from .engine import config as cfg_mod
from .models import Card, CashflowSignal, Customer, Transaction

ESSENTIAL_MCC = ["GROCERY", "FUEL", "UTILITIES", "MEDICAL", "EDUCATION"]
DISCRETIONARY_MCC = ["DINING", "SHOPPING", "ENTERTAINMENT", "APPAREL"]
ASPIRATIONAL_MCC = ["TRAVEL_INTL", "LUXURY_RETAIL", "FINE_DINING", "TRAVEL_DOM"]
SEASONAL_MCC = ["TRAVEL_INTL", "TRAVEL_DOM", "LUXURY_RETAIL", "FESTIVE_RETAIL"]
CITIES = ["Bengaluru", "Mumbai", "Delhi", "Pune", "Hyderabad", "Chennai"]

MQ = {"ESSENTIAL": 0.50, "DISCRETIONARY": 0.65, "ASPIRATIONAL": 0.85}


def _window(card_id, day_lo, day_hi, total, shares, seasonal=False, recurrence=0.0,
            mq_offset=0.0, declines=0):
    """Generate transactions for one 30-day window matching a target total + mix."""
    rows = []
    for cat, share in shares.items():
        if share <= 0:
            continue
        cat_total = total * share
        n = max(1, round(share * 7))
        each = cat_total / n
        for _ in range(n):
            if cat == "ASPIRATIONAL":
                mcc = random.choice(SEASONAL_MCC if seasonal else ASPIRATIONAL_MCC)
            elif cat == "DISCRETIONARY":
                mcc = random.choice(DISCRETIONARY_MCC)
            else:
                mcc = random.choice(ESSENTIAL_MCC)
            rows.append(Transaction(
                id=f"TXN-{uuid.uuid4().hex[:10].upper()}",
                card_id=card_id,
                amount=round(each * random.uniform(0.8, 1.2), 2),
                category_class=cat,
                merchant_category=mcc,
                merchant_quality=min(1.0, max(0.1, MQ[cat] + mq_offset)),
                is_recurring=(cat in {"ESSENTIAL", "DISCRETIONARY"} and random.random() < recurrence),
                is_declined=False,
                merchant_city=random.choice(CITIES),
                timestamp=datetime.utcnow() - timedelta(days=random.randint(day_lo, day_hi - 1),
                                                         hours=random.randint(0, 23)),
            ))
    for _ in range(declines):
        rows.append(Transaction(
            id=f"TXN-{uuid.uuid4().hex[:10].upper()}", card_id=card_id,
            amount=round(total * 0.4, 2), category_class="ASPIRATIONAL",
            merchant_category=random.choice(ASPIRATIONAL_MCC), merchant_quality=0.6,
            is_recurring=False, is_declined=True, merchant_city=random.choice(CITIES),
            timestamp=datetime.utcnow() - timedelta(days=random.randint(day_lo, day_hi - 1)),
        ))
    return rows


def add(db, *, cif, name, profile, entity="RETAIL", segment="MASS", employment="SALARIED",
        programme="AU-LIT", bureau, dpd=0, vintage=18, stated_income, external_debt=0.0,
        limit, outstanding, statement, last_payment, min_due, peak_drawn=None,
        months_since_change=12, months_inactive=0, signals=None, fraud=False, legal=False,
        aa_consent=True, trade_dpd=None, dscr=None, wc_util=None, promoter_score=None):
    cust = Customer(
        id=cif, name=name, entity_type=entity, segment=segment, employment_type=employment,
        programme_id=programme, bureau_score=bureau, dpd_max_12m=dpd,
        account_vintage_months=vintage, stated_income=stated_income, external_debt=external_debt,
        fraud_flag=fraud, legal_block_flag=legal, aa_consent_active=aa_consent,
        trade_dpd_days=trade_dpd, dscr=dscr, working_capital_utilization=wc_util,
        promoter_score=promoter_score,
    )
    db.add(cust)
    card_id = f"CARD-{cif.split('-')[-1]}"
    db.add(Card(
        id=card_id, customer_id=cif, current_limit=limit, outstanding=outstanding,
        statement_balance=statement, last_payment=last_payment, min_due_last=min_due,
        peak_drawn_12m=peak_drawn if peak_drawn is not None else outstanding,
        months_since_last_change=months_since_change, months_inactive=months_inactive,
        opened_at=datetime.utcnow() - timedelta(days=vintage * 30),
    ))
    for src, amt, reg in (signals or []):
        db.add(CashflowSignal(customer_id=cif, source=src, monthly_amount=amt, regularity=reg,
                              as_of=datetime.utcnow() - timedelta(days=random.randint(0, 20))))

    # Transaction windows: w2 (60-90d), w1 (30-60d), w0 (0-30d)
    for win_key, (lo, hi) in (("w2", (60, 90)), ("w1", (30, 60)), ("w0", (0, 30))):
        spec = profile[win_key]
        db.add_all(_window(card_id, lo, hi, spec["total"], spec["mix"],
                           seasonal=spec.get("seasonal", False),
                           recurrence=spec.get("recurrence", 0.2),
                           mq_offset=spec.get("mq_offset", 0.0),
                           declines=spec.get("declines", 0)))


# ── Spend-pattern profiles ───────────────────────────────────────────────────
GROWTH = {  # accelerating, drifting up-market
    "w2": {"total": 40_000, "mix": {"ESSENTIAL": 0.7, "DISCRETIONARY": 0.25, "ASPIRATIONAL": 0.05}},
    "w1": {"total": 48_000, "mix": {"ESSENTIAL": 0.6, "DISCRETIONARY": 0.3, "ASPIRATIONAL": 0.1}, "mq_offset": 0.03},
    "w0": {"total": 78_000, "mix": {"ESSENTIAL": 0.45, "DISCRETIONARY": 0.35, "ASPIRATIONAL": 0.2}, "mq_offset": 0.08},
}
DISTRESS = {  # spend up but quality flat/declining, plugging a hole
    "w2": {"total": 55_000, "mix": {"ESSENTIAL": 0.7, "DISCRETIONARY": 0.25, "ASPIRATIONAL": 0.05}},
    "w1": {"total": 62_000, "mix": {"ESSENTIAL": 0.78, "DISCRETIONARY": 0.2, "ASPIRATIONAL": 0.02}, "mq_offset": -0.05},
    "w0": {"total": 84_000, "mix": {"ESSENTIAL": 0.85, "DISCRETIONARY": 0.13, "ASPIRATIONAL": 0.02}, "mq_offset": -0.1, "declines": 2},
}
SEASONAL = {  # big spike concentrated in festive/travel
    "w2": {"total": 35_000, "mix": {"ESSENTIAL": 0.8, "DISCRETIONARY": 0.18, "ASPIRATIONAL": 0.02}},
    "w1": {"total": 38_000, "mix": {"ESSENTIAL": 0.78, "DISCRETIONARY": 0.2, "ASPIRATIONAL": 0.02}},
    "w0": {"total": 92_000, "mix": {"ESSENTIAL": 0.35, "DISCRETIONARY": 0.15, "ASPIRATIONAL": 0.5}, "seasonal": True},
}
STABLE = {  # flat, predictable — no momentum
    "w2": {"total": 45_000, "mix": {"ESSENTIAL": 0.66, "DISCRETIONARY": 0.3, "ASPIRATIONAL": 0.04}, "recurrence": 0.45},
    "w1": {"total": 44_000, "mix": {"ESSENTIAL": 0.66, "DISCRETIONARY": 0.3, "ASPIRATIONAL": 0.04}, "recurrence": 0.45},
    "w0": {"total": 43_000, "mix": {"ESSENTIAL": 0.66, "DISCRETIONARY": 0.3, "ASPIRATIONAL": 0.04}, "recurrence": 0.45},
}
DORMANT = {  # almost no spend
    "w2": {"total": 1_500, "mix": {"ESSENTIAL": 1.0, "DISCRETIONARY": 0.0, "ASPIRATIONAL": 0.0}},
    "w1": {"total": 1_200, "mix": {"ESSENTIAL": 1.0, "DISCRETIONARY": 0.0, "ASPIRATIONAL": 0.0}},
    "w0": {"total": 1_000, "mix": {"ESSENTIAL": 1.0, "DISCRETIONARY": 0.0, "ASPIRATIONAL": 0.0}},
}


def seed(reset: bool = True):
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    random.seed(7)
    try:
        cfg_mod.ensure_seeded(db)

        # 1. Tier 1 × Growth — elite transactor, high util → aggressive offer
        add(db, cif="CIF-1001", name="Aarav Mehta", profile=GROWTH, segment="PREMIUM",
            bureau=805, dpd=0, vintage=26, stated_income=95_000, external_debt=8_000,
            limit=150_000, outstanding=95_000, statement=92_000, last_payment=70_000, min_due=4_600,
            signals=[("CBS_SALARY", 130_000, 0.96), ("AA", 128_000, 0.95)])

        # 2. Tier 1 × Growth — premium, large headroom
        add(db, cif="CIF-1002", name="Diya Sharma", profile=GROWTH, segment="PREMIUM",
            bureau=822, dpd=0, vintage=30, stated_income=260_000, external_debt=20_000,
            limit=300_000, outstanding=205_000, statement=190_000, last_payment=160_000, min_due=9_500,
            signals=[("CBS_SALARY", 320_000, 0.97), ("AA", 318_000, 0.96)])

        # 3. Tier 2 × Seasonal — festive spike, prepays → temporary offer
        add(db, cif="CIF-1003", name="Rohan Patel", profile=SEASONAL, segment="MASS",
            bureau=748, dpd=0, vintage=20, stated_income=90_000, external_debt=6_000,
            limit=120_000, outstanding=78_000, statement=70_000, last_payment=68_500, min_due=3_500,
            signals=[("CBS_SALARY", 92_000, 0.66), ("AA", 90_000, 0.64)])

        # 4. Tier 2 × Neutral — stable revolver → maintain
        add(db, cif="CIF-1004", name="Kavya Reddy", profile=STABLE, segment="MASS",
            bureau=752, dpd=0, vintage=24, stated_income=72_000, external_debt=10_000,
            limit=110_000, outstanding=44_000, statement=43_000, last_payment=20_000, min_due=2_100,
            signals=[("CBS_SALARY", 73_000, 0.9), ("AA", 72_000, 0.9)])

        # 5. Tier 3 × Distress — min-due dependency, erratic inflow → buffered cut
        add(db, cif="CIF-1005", name="Vikram Singh", profile=DISTRESS, segment="MASS",
            bureau=694, dpd=0, vintage=16, stated_income=62_000, external_debt=14_000,
            limit=120_000, outstanding=82_000, statement=95_000, last_payment=12_000, min_due=10_500,
            signals=[("CBS_SALARY", 60_000, 0.46), ("UPI_INFLOW", 18_000, 0.4)])

        # 6. Tier 4 × Knockout — active 30+ DPD bypasses scoring
        add(db, cif="CIF-1006", name="Ishaan Joshi", profile=GROWTH, segment="MASS",
            bureau=662, dpd=45, vintage=14, stated_income=70_000, external_debt=15_000,
            limit=110_000, outstanding=70_000, statement=66_000, last_payment=20_000, min_due=6_500,
            signals=[("CBS_SALARY", 88_000, 0.7)])

        # 7. Tier 1 × Growth — premium, high util → big offer (capacity-bounded)
        add(db, cif="CIF-1007", name="Ananya Iyer", profile=GROWTH, segment="PREMIUM",
            bureau=830, dpd=0, vintage=34, stated_income=230_000, external_debt=25_000,
            limit=260_000, outstanding=175_000, statement=165_000, last_payment=140_000, min_due=8_200,
            signals=[("CBS_SALARY", 340_000, 0.97), ("AA", 335_000, 0.96)])

        # 8. Growth signals but FREQUENCY GATE — increased 2 months ago → held
        add(db, cif="CIF-1008", name="Aditya Nair", profile=GROWTH, segment="MASS",
            bureau=770, dpd=0, vintage=12, stated_income=85_000, external_debt=5_000,
            limit=120_000, outstanding=72_000, statement=68_000, last_payment=55_000, min_due=3_400,
            months_since_change=2,
            signals=[("CBS_SALARY", 110_000, 0.95), ("AA", 108_000, 0.94)])

        # 9. Tier 3 × Growth — THE showcase cell: thin-file climbing → cautious temp offer
        add(db, cif="CIF-1009", name="Meera Krishnan", profile=GROWTH, segment="THIN_FILE",
            bureau=646, dpd=0, vintage=9, stated_income=52_000, external_debt=4_000,
            limit=70_000, outstanding=31_000, statement=28_000, last_payment=15_000, min_due=1_400,
            signals=[("CBS_SALARY", 60_000, 0.74), ("AA", 58_000, 0.72)])

        # 10. INACTIVITY right-sizing — dormant undrawn limit → capital optimisation cut
        add(db, cif="CIF-1010", name="Rahul Kapoor", profile=DORMANT, segment="MASS",
            bureau=778, dpd=0, vintage=40, stated_income=80_000, external_debt=6_000,
            limit=150_000, outstanding=4_000, statement=4_000, last_payment=4_000, min_due=200,
            peak_drawn=28_000, months_inactive=14,
            signals=[("CBS_SALARY", 84_000, 0.93), ("AA", 83_000, 0.92)])

        # 11. Tier 4 × Knockout — active fraud flag → freeze
        add(db, cif="CIF-1011", name="Priya Banerjee", profile=STABLE, segment="MASS",
            bureau=740, dpd=0, vintage=18, stated_income=88_000, external_debt=9_000,
            limit=130_000, outstanding=60_000, statement=58_000, last_payment=40_000, min_due=2_800,
            fraud=True, signals=[("CBS_SALARY", 90_000, 0.9)])

        # 12. Tier 2 × Growth — clean step-up
        add(db, cif="CIF-1012", name="Karan Malhotra", profile=GROWTH, segment="MASS",
            bureau=758, dpd=0, vintage=22, stated_income=95_000, external_debt=12_000,
            limit=130_000, outstanding=82_000, statement=78_000, last_payment=60_000, min_due=3_900,
            signals=[("CBS_SALARY", 120_000, 0.93), ("AA", 118_000, 0.92)])

        # 13. Tier 3 × Distress — self-employed, irregular inflow → cut
        add(db, cif="CIF-1013", name="Sneha Pillai", profile=DISTRESS, segment="MASS",
            employment="SELF_EMPLOYED", bureau=704, dpd=0, vintage=15, stated_income=78_000,
            external_debt=14_000, limit=140_000, outstanding=95_000, statement=112_000,
            last_payment=15_000, min_due=12_000,
            signals=[("GST", 64_000, 0.45), ("UPI_INFLOW", 52_000, 0.4), ("AA", 58_000, 0.42)])

        # 14. MSME × Distress — trade-credit DPD double-gate early warning → cut
        add(db, cif="CIF-2001", name="Patel Traders Pvt Ltd", profile=DISTRESS, entity="MSME",
            segment="MASS", employment="BUSINESS", programme="FED-SCAPIA", bureau=712, dpd=0,
            vintage=28, stated_income=180_000, external_debt=40_000, limit=400_000,
            outstanding=300_000, statement=310_000, last_payment=60_000, min_due=30_000,
            trade_dpd=25, dscr=0.95, wc_util=0.92, promoter_score=58,
            signals=[("GST", 190_000, 0.5), ("TRADE", 150_000, 0.45), ("AA", 175_000, 0.48)])

        # 15. MSME × Growth — healthy trade settlement, strong DSCR → offer
        add(db, cif="CIF-2002", name="Sharma Enterprises", profile=GROWTH, entity="MSME",
            segment="MASS", employment="BUSINESS", programme="FED-SCAPIA", bureau=775, dpd=0,
            vintage=32, stated_income=220_000, external_debt=40_000, limit=350_000,
            outstanding=230_000, statement=215_000, last_payment=180_000, min_due=10_500,
            trade_dpd=0, dscr=1.6, wc_util=0.5, promoter_score=80,
            signals=[("GST", 260_000, 0.9), ("TRADE", 240_000, 0.88), ("AA", 250_000, 0.9)])

        db.commit()
        print(f"Seeded {db.query(Customer).count()} customers across the Risk × Intent matrix.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
