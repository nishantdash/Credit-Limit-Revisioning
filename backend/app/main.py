from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, engine
from .routes import analytics, customers, decisions, hitl, ingest, triggers, webhooks

app = FastAPI(
    title="CLR — Credit Limit Revisioning Engine",
    description="Continuous, event-driven, AI-personalised credit-limit management prototype.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(customers.router)
app.include_router(decisions.router)
app.include_router(hitl.router)
app.include_router(triggers.router)
app.include_router(webhooks.router)
app.include_router(ingest.router)
app.include_router(analytics.router)


@app.get("/")
def root():
    return {
        "name": "CLR",
        "tagline": "Continuous credit-limit revisioning engine",
        "layers": {
            "L1_data": "/customers, /webhooks/hyperface/event",
            "L2_ai": "internal — behavioral, income, risk, explainer",
            "L3_decision": "/triggers/fire, /triggers/periodic-sweep, /hitl/queue",
            "L5_integration": "/webhooks/hyperface/outbound/{decision_id}",
            "L6_audit": "/analytics/audit-log",
            "L7_analytics": "/analytics/funnel, /analytics/roi",
        },
    }


@app.get("/health")
def health():
    return {"status": "ok"}
