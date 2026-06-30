import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, SessionLocal, engine
from .engine import config as cfg_mod
from .routes import (
    actions,
    analytics,
    config as config_route,
    customers,
    decisions,
    ingest,
    offers,
    review,
    triggers,
    webhooks,
)

app = FastAPI(
    title="CLR — Intent-Driven Credit Limit Revisioning Engine",
    description=(
        "Real-time, intent-driven credit-limit revisioning. Disambiguates growth "
        "vs distress vs seasonal, emits a four-part decision (direction, magnitude, "
        "duration, confidence), and orchestrates consent-asymmetric offer/action "
        "pipelines on India's AA + DPDP + RBI rails."
    ),
    version="1.0.0",
)

# Local dev origins, plus any set via CORS_ORIGINS (comma-separated) on the host.
# The regex additionally allows any *.vercel.app domain so preview deploys work
# without reconfiguring on every Vercel URL change.
_cors_env = os.getenv("CORS_ORIGINS", "")
_cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()] or [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

# Ensure the three tenant-config presets exist on boot.
_db = SessionLocal()
try:
    cfg_mod.ensure_seeded(_db)
finally:
    _db.close()

for r in (config_route, customers, decisions, offers, actions, review,
          triggers, webhooks, ingest, analytics):
    app.include_router(r.router)


@app.get("/")
def root():
    return {
        "name": "CLR",
        "tagline": "Real-time, intent-driven credit limit revisioning",
        "pipeline": "knockout → 5 signal layers → risk/tier → intent → Risk×Intent matrix "
                    "→ capacity/buffer formulas → anti-spiral guardrails → offer/action split",
        "endpoints": {
            "config": "/config (Bank/NBFC/SFB)",
            "customers": "/customers",
            "decisions": "/decisions",
            "offers": "/offers (consent-gated increases)",
            "actions": "/actions (applied decreases)",
            "review": "/review/queue (low-confidence / manual)",
            "triggers": "/triggers/fire, /triggers/micro-review-sweep",
            "analytics": "/analytics/funnel, /analytics/roi, /analytics/guardrails",
        },
    }


@app.get("/health")
def health():
    return {"status": "ok"}
