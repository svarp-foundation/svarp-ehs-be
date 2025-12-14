from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import delete
from typing import Dict, List

from app.db.company_session import get_company_db
from app.db.master import SessionLocal
from app.models.company_db.audit import Audit
from app.models.company_db.audit_team import AuditTeam
from app.models.company_db.site import Site
from app.models.company_db.finding import Finding
from app.models.user import User
from app.schemas.audit import AuditCreate, AuditOut, AuditUpdate

router = APIRouter(prefix="/audit", tags=["Audit"])


# -------------------- MASTER DB --------------------
def get_master_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------- CREATE AUDIT --------------------
@router.post("/create", response_model=Dict, status_code=201)
def create_audit(data: AuditCreate, db: Session = Depends(get_company_db)):
    site = db.query(Site).filter(Site.id == data.site_id).first()
    if not site:
        raise HTTPException(400, "Invalid site_id")

    audit = Audit(
        title=data.title,
        audit_type=data.audit_type,
        site_id=data.site_id,
        scope=data.scope,
        start_date=data.start_date,
        end_date=data.end_date,
        checklist_id=data.checklist_id,
        status="planned",
    )

    db.add(audit)
    db.commit()
    db.refresh(audit)

    return {"message": "Audit created", "audit_id": audit.id}


# -------------------- LIST AUDITS --------------------
@router.get("/list", response_model=List[AuditOut])
def list_audits(db: Session = Depends(get_company_db)):
    rows = db.query(Audit).order_by(Audit.id.desc()).all()
    audits = []

    for a in rows:
        site = db.query(Site).filter(Site.id == a.site_id).first()
        audits.append({
            "id": a.id,
            "title": a.title,
            "audit_type": a.audit_type,
            "site_id": a.site_id,
            "site_name": site.name if site else None,
            "scope": a.scope,
            "start_date": a.start_date,
            "end_date": a.end_date,
            "status": a.status,
            "checklist_id": a.checklist_id,
            "created_at": a.created_at,
        })

    return audits


# -------------------- AUDIT DETAIL --------------------
@router.get("/detail/{audit_id}", response_model=Dict)
def audit_detail(audit_id: int, db: Session = Depends(get_company_db)):
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        raise HTTPException(404, "Audit not found")

    site = db.query(Site).filter(Site.id == audit.site_id).first()

    team_rows = db.query(AuditTeam).filter(AuditTeam.audit_id == audit_id).all()
    team = []

    master_db = SessionLocal()
    for t in team_rows:
        user = master_db.query(User).filter(User.id == t.auditor_id).first()
        if user:
            team.append({
                "user_id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
            })

    return {
        "audit": {
            "id": audit.id,
            "title": audit.title,
            "audit_type": audit.audit_type,
            "site_id": audit.site_id,
            "site_name": site.name if site else None,
            "scope": audit.scope,
            "start_date": audit.start_date,
            "end_date": audit.end_date,
            "status": audit.status,
            "created_at": audit.created_at,
        },
        "team": team,
    }


# -------------------- UPDATE AUDIT --------------------
@router.patch("/{audit_id}", response_model=Dict)
def update_audit(audit_id: int, data: AuditUpdate, db: Session = Depends(get_company_db)):
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        raise HTTPException(404, "Audit not found")

    for k, v in data.dict(exclude_unset=True).items():
        setattr(audit, k, v)

    db.commit()
    return {"message": "Audit updated", "audit_id": audit.id}


# -------------------- DELETE AUDIT (SAFE) --------------------
@router.delete("/{audit_id}")
def delete_audit(audit_id: int, db: Session = Depends(get_company_db)):
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        raise HTTPException(404, "Audit not found")

    if db.query(Finding).filter(Finding.audit_id == audit_id).count() > 0:
        raise HTTPException(400, "Cannot delete audit with findings")

    db.query(AuditTeam).filter(AuditTeam.audit_id == audit_id).delete()
    db.delete(audit)
    db.commit()

    return {"message": "Audit deleted"}


# -------------------- AVAILABLE AUDITORS --------------------
@router.get("/available-auditors")
def available_auditors(db: Session = Depends(get_master_db)):
    users = db.query(User).filter(User.role.in_(["admin", "auditor"])).all()
    return [
        {"id": u.id, "name": u.name, "email": u.email, "role": u.role}
        for u in users
    ]


# -------------------- UPDATE AUDIT TEAM (ONLY API) --------------------
@router.put("/team/{audit_id}", response_model=Dict)
def update_audit_team(
    audit_id: int,
    auditor_ids: List[int],
    db: Session = Depends(get_company_db),
    master_db: Session = Depends(get_master_db),
):
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        raise HTTPException(404, "Audit not found")

    for uid in auditor_ids:
        if not master_db.query(User).filter(User.id == uid).first():
            raise HTTPException(400, f"Invalid auditor_id {uid}")

    db.execute(delete(AuditTeam).where(AuditTeam.audit_id == audit_id))

    for uid in auditor_ids:
        db.add(AuditTeam(audit_id=audit_id, auditor_id=uid))

    db.commit()
    return {"message": "Audit team updated"}
