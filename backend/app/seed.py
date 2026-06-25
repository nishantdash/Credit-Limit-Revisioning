"""Seed the SQLite DB with a mix of customer archetypes so the demo shows a
realistic spread of UPGRADE / DOWNGRADE / FREEZE decisions across the funnel.

Archetypes:
  - Salaried, improving income, healthy spend  → expect UPGRADE
  - Salaried, large limit jump (>50k delta)    → UPGRADE w/ HITL
  - Self-employed, GST/UPI signal growth       → UPGRADE
  - Stable customer, no income change          → FREEZE
  - High utilisation, dropping spend           → DOWNGRADE
  - DPD in last 12m (policy violation)         → FREEZE via policy guardrail
  - Premium customer, tier-upgrade eligible    → UPGRADE + tier change
"""
import random
import uuid
from datetime import datetime, timedelta

from .db import Base, SessionLocal, engine
from .models import (
    Card,
    Customer,
    IncomeSignal,
    PolicyConfig,
    Transaction,
)


PROGRAMMES = ["AU-LIT", "FED-SCAPIA", "RBL-INDIE"]
CITIES = ["Bengaluru", "Mumbai", "Delhi", "Pune", "Hyderabad", "Chennai"]
PREMIUM_MCC = ["FINE_DINING", "TRAVEL_INTL", "LUXURY_RETAIL", "SAAS"]
STANDARD_MCC = ["GROCERY", "FUEL", "UTILITIES", "MEDICAL", "EDUCATION"]


def _txn(card_id: str, days_ago: int, amount: float, premium: bool, city: str) -> Transaction:
    return Transaction(
        id=f"TXN-{uuid.uuid4().hex[:10].upper()}",
        card_id=card_id,
        amount=amount,
        merchant_category=random.choice(PREMIUM_MCC if premium else STANDARD_MCC),
        merchant_tier="PREMIUM" if premium else "STANDARD",
        merchant_city=city,
        timestamp=datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23)),
    )


def _seed_customer(
    db,
    *,
    cif: str,
    name: str,
    segment: str,
    bureau: int,
    stated_income: float,
    employment: str,
    limit: float,
    balance: float,
    tier: str,
    months_at_limit: int,
    dpd: int,
    programme: str,
    income_signals: list[tuple[str, float]],
    spend_pattern: str,  # "improving" / "stable" / "high_util_dropping"
) -> Customer:
    customer = Customer(
        id=cif,
        name=name,
        segment=segment,
        bureau_score=bureau,
        programme_id=programme,
        dpd_max_12m=dpd,
        stated_income=stated_income,
        employment_type=employment,
    )
    db.add(customer)

    card_id = f"CARD-{cif.split('-')[-1]}"
    card = Card(
        id=card_id,
        customer_id=cif,
        current_limit=limit,
        current_balance=balance,
        benefits_tier=tier,
        months_at_current_limit=months_at_limit,
        opened_at=datetime.utcnow() - timedelta(days=months_at_limit * 30 + 60),
    )
    db.add(card)

    for source, amt in income_signals:
        db.add(IncomeSignal(
            customer_id=cif,
            source=source,
            monthly_amount=amt,
            as_of=datetime.utcnow() - timedelta(days=random.randint(0, 25)),
        ))

    city = random.choice(CITIES)
    # Generate 90 days of transactions per pattern
    if spend_pattern == "improving":
        # Last-30 spend ~50% higher than prior-30, premium mix increasing.
        for d in range(60, 31, -1):
            db.add(_txn(card_id, d, random.uniform(1500, 4500), random.random() < 0.15, city))
        for d in range(30, 0, -1):
            db.add(_txn(card_id, d, random.uniform(2500, 7000), random.random() < 0.45, city))
    elif spend_pattern == "high_util_dropping":
        for d in range(60, 31, -1):
            db.add(_txn(card_id, d, random.uniform(4000, 9000), random.random() < 0.20, city))
        for d in range(30, 0, -1):
            db.add(_txn(card_id, d, random.uniform(1000, 3000), random.random() < 0.10, city))
    else:  # stable
        for d in range(60, 0, -1):
            db.add(_txn(card_id, d, random.uniform(2000, 5000), random.random() < 0.20, city))

    return customer


def seed(reset: bool = True):
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        db.add(PolicyConfig())

        random.seed(42)

        # 1. Salaried, improving income, clean record — UPGRADE auto
        _seed_customer(
            db,
            cif="CIF-1001", name="Aarav Mehta", segment="MASS",
            bureau=782, stated_income=70_000, employment="SALARIED",
            limit=100_000, balance=42_000, tier="SILVER",
            months_at_limit=14, dpd=0, programme="AU-LIT",
            income_signals=[("CBS_SALARY", 92_000), ("AA", 96_000), ("UPI_INFLOW", 14_000)],
            spend_pattern="improving",
        )

        # 2. Salaried, big jump → HITL
        _seed_customer(
            db,
            cif="CIF-1002", name="Diya Sharma", segment="PREMIUM",
            bureau=815, stated_income=180_000, employment="SALARIED",
            limit=200_000, balance=110_000, tier="GOLD",
            months_at_limit=18, dpd=0, programme="AU-LIT",
            income_signals=[("CBS_SALARY", 260_000), ("AA", 255_000)],
            spend_pattern="improving",
        )

        # 3. Self-employed, GST + UPI signalling growth
        _seed_customer(
            db,
            cif="CIF-1003", name="Rohan Patel", segment="MASS",
            bureau=755, stated_income=65_000, employment="SELF_EMPLOYED",
            limit=90_000, balance=38_000, tier="SILVER",
            months_at_limit=10, dpd=0, programme="FED-SCAPIA",
            income_signals=[("GST", 85_000), ("UPI_INFLOW", 92_000), ("AA", 78_000)],
            spend_pattern="improving",
        )

        # 4. Stable — FREEZE
        _seed_customer(
            db,
            cif="CIF-1004", name="Kavya Reddy", segment="MASS",
            bureau=740, stated_income=55_000, employment="SALARIED",
            limit=80_000, balance=30_000, tier="SILVER",
            months_at_limit=9, dpd=0, programme="RBL-INDIE",
            income_signals=[("CBS_SALARY", 56_000), ("AA", 57_000)],
            spend_pattern="stable",
        )

        # 5. High utilisation, dropping spend — DOWNGRADE
        _seed_customer(
            db,
            cif="CIF-1005", name="Vikram Singh", segment="MASS",
            bureau=685, stated_income=60_000, employment="SALARIED",
            limit=120_000, balance=108_000, tier="SILVER",
            months_at_limit=11, dpd=15, programme="AU-LIT",
            income_signals=[("CBS_SALARY", 58_000), ("AA", 55_000)],
            spend_pattern="high_util_dropping",
        )

        # 6. DPD violation — policy freezes any upgrade
        _seed_customer(
            db,
            cif="CIF-1006", name="Ishaan Joshi", segment="MASS",
            bureau=692, stated_income=72_000, employment="SALARIED",
            limit=110_000, balance=48_000, tier="SILVER",
            months_at_limit=12, dpd=75, programme="FED-SCAPIA",
            income_signals=[("CBS_SALARY", 90_000), ("AA", 91_000)],
            spend_pattern="improving",
        )

        # 7. Premium customer, tier UPGRADE
        _seed_customer(
            db,
            cif="CIF-1007", name="Ananya Iyer", segment="PREMIUM",
            bureau=830, stated_income=220_000, employment="SALARIED",
            limit=240_000, balance=130_000, tier="GOLD",
            months_at_limit=20, dpd=0, programme="AU-LIT",
            income_signals=[("CBS_SALARY", 340_000), ("AA", 335_000)],
            spend_pattern="improving",
        )

        # 8. Tenure too short — policy violation
        _seed_customer(
            db,
            cif="CIF-1008", name="Aditya Nair", segment="MASS",
            bureau=760, stated_income=60_000, employment="SALARIED",
            limit=70_000, balance=22_000, tier="SILVER",
            months_at_limit=4, dpd=0, programme="RBL-INDIE",
            income_signals=[("CBS_SALARY", 85_000), ("AA", 84_000)],
            spend_pattern="improving",
        )

        # 9. New-to-credit, very low bureau — FREEZE
        _seed_customer(
            db,
            cif="CIF-1009", name="Meera Krishnan", segment="MASS",
            bureau=620, stated_income=45_000, employment="SALARIED",
            limit=50_000, balance=15_000, tier="SILVER",
            months_at_limit=8, dpd=20, programme="AU-LIT",
            income_signals=[("CBS_SALARY", 46_000)],
            spend_pattern="stable",
        )

        # 10. Self-employed, declining business — DOWNGRADE
        _seed_customer(
            db,
            cif="CIF-1010", name="Rahul Kapoor", segment="MASS",
            bureau=702, stated_income=80_000, employment="SELF_EMPLOYED",
            limit=150_000, balance=132_000, tier="SILVER",
            months_at_limit=15, dpd=10, programme="FED-SCAPIA",
            income_signals=[("GST", 55_000), ("UPI_INFLOW", 48_000), ("AA", 52_000)],
            spend_pattern="high_util_dropping",
        )

        # 11-15. Five more salaried, mostly upgrades with mixed signals.
        names = [
            ("CIF-1011", "Priya Banerjee", 770, 85_000, 100_000, 0, "improving"),
            ("CIF-1012", "Karan Malhotra", 745, 95_000, 130_000, 0, "improving"),
            ("CIF-1013", "Sneha Pillai", 760, 75_000, 90_000, 0, "stable"),
            ("CIF-1014", "Arjun Verma", 715, 65_000, 95_000, 20, "high_util_dropping"),
            ("CIF-1015", "Tara Bose", 800, 150_000, 180_000, 0, "improving"),
        ]
        for cif, name, bureau, stated, limit, dpd, pattern in names:
            growth = 1.4 if pattern == "improving" else (0.85 if pattern == "high_util_dropping" else 1.05)
            _seed_customer(
                db,
                cif=cif, name=name, segment="MASS" if stated < 120_000 else "PREMIUM",
                bureau=bureau, stated_income=stated, employment="SALARIED",
                limit=limit, balance=limit * (0.85 if pattern == "high_util_dropping" else 0.42),
                tier="SILVER" if limit < 100_000 else "GOLD",
                months_at_limit=random.randint(8, 22), dpd=dpd,
                programme=random.choice(PROGRAMMES),
                income_signals=[("CBS_SALARY", stated * growth), ("AA", stated * growth * 0.98)],
                spend_pattern=pattern,
            )

        db.commit()
        print(f"Seeded {db.query(Customer).count()} customers.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
