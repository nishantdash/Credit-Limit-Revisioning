"""Tenant configuration routes (§8) — the configurable SaaS layer."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..engine import config as cfg_mod
from ..models import AuditLog, TenantConfig
from ..schemas import ConfigPatch, ConfigSwitch

router = APIRouter(prefix="/config", tags=["config"])


def _row_to_dict(row: TenantConfig) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "archetype": row.archetype,
        "active": row.active,
        "config": row.config,
        "updated_at": row.updated_at,
    }


@router.get("")
def get_active(db: Session = Depends(get_db)):
    cfg_mod.ensure_seeded(db)
    row = db.query(TenantConfig).filter(TenantConfig.active.is_(True)).first()
    return _row_to_dict(row)


@router.get("/presets")
def list_presets(db: Session = Depends(get_db)):
    cfg_mod.ensure_seeded(db)
    rows = db.query(TenantConfig).order_by(TenantConfig.id).all()
    return [_row_to_dict(r) for r in rows]


@router.post("/activate")
def activate(req: ConfigSwitch, db: Session = Depends(get_db)):
    arch = req.archetype.upper()
    if arch not in cfg_mod.PRESETS:
        raise HTTPException(400, f"Unknown archetype {arch}")
    cfg_mod.ensure_seeded(db)
    for row in db.query(TenantConfig).all():
        row.active = row.archetype == arch
    db.add(AuditLog(entity_type="TenantConfig", entity_id=arch, action="ACTIVATED",
                    actor="config_admin", payload={"archetype": arch}))
    db.commit()
    row = db.query(TenantConfig).filter(TenantConfig.archetype == arch).first()
    return _row_to_dict(row)


@router.put("")
def patch_active(patch: ConfigPatch, db: Session = Depends(get_db)):
    row = db.query(TenantConfig).filter(TenantConfig.active.is_(True)).first()
    if not row:
        raise HTTPException(404, "No active tenant config")
    merged = {**row.config, **patch.config}
    row.config = merged
    row.updated_at = datetime.utcnow()
    db.add(AuditLog(entity_type="TenantConfig", entity_id=row.archetype, action="PATCHED",
                    actor="config_admin", payload={"keys": list(patch.config)}))
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)
