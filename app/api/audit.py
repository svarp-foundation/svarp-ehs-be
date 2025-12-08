from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List

from app.schemas.audit import AuditCreate, AuditOut
from app.models.company_db.audit import Audit
from app.models.company_db.audit_team import AuditTeam
from app.db.company_session import get_company_db
from app.models.company_db.site import Site
from app.models.user import User  # assuming master user table for auditors

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.post("/create", response_model=Dict, status_code=201)
def create_audit(data: AuditCreate, db: Session = Depends(get_company_db)):
    # Validate site
    site = db.query(Site).filter(Site.id == data.site_id).first()
    if not site:
        raise HTTPException(400, "Invalid site_id: Site does not exist")

    # Validate auditors → must be valid user ids
    if data.auditor_ids:
        for uid in data.auditor_ids:
            user = db.query(User).filter(User.id == uid).first()
            if not user:
                raise HTTPException(400, f"Invalid auditor_id: {uid} does not exist")

    # Create main audit
    audit = Audit(
        title=data.title,
        audit_type=data.audit_type,
        site_id=data.site_id,
        scope=data.scope,
        start_date=data.start_date,
        end_date=data.end_date,
        checklist_id=data.checklist_id,
        status="planned",  # default
    )

    db.add(audit)
    db.commit()
    db.refresh(audit)

    # Add audit team members
    for auditor in (data.auditor_ids or []):
        db.add(AuditTeam(audit_id=audit.id, auditor_id=auditor))
    db.commit()

    return {"message": "Audit created successfully", "audit_id": audit.id}
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
            "created_at": a.created_at.isoformat() if getattr(a, "created_at", None) else None
        })

    return audits
@router.get("/detail/{audit_id}", response_model=Dict)
def audit_detail(audit_id: int, db: Session = Depends(get_company_db)):
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        raise HTTPException(404, "Audit not found")

    site = db.query(Site).filter(Site.id == audit.site_id).first()

    # team members list
    team_rows = db.query(AuditTeam).filter(AuditTeam.audit_id == audit_id).all()

    team = []
    for t in team_rows:
        member = db.query(User).filter(User.id == t.auditor_id).first()
        if member:
            team.append({
                "user_id": member.id,
                "name": member.name,
                "email": member.email,
                "role": member.role
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
            "created_at": audit.created_at.isoformat() if getattr(audit, "created_at", None) else None,
        },
        "team": team
    }
