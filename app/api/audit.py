from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.audit import AuditCreate
from app.models.company_db.audit import Audit
from app.models.company_db.audit_team import AuditTeam
from app.db.company_session import get_company_db
from app.models.company_db.site import Site

router = APIRouter(prefix="/audit", tags=["Audit"])

@router.post("/create")
def create_audit(data: AuditCreate, db: Session = Depends(get_company_db)):

    # 🔥 Validate site_id
    site = db.query(Site).filter(Site.id == data.site_id).first()
    if not site:
        raise HTTPException(status_code=400, detail="Invalid site_id: site does not exist")

    audit = Audit(
        title=data.title,
        audit_type=data.audit_type,
        site_id=data.site_id,
        scope=data.scope,
        start_date=data.start_date,
        end_date=data.end_date,
        checklist_id=data.checklist_id,
    )

    db.add(audit)
    db.commit()
    db.refresh(audit)

    # Auditor/team
    for auditor in data.auditor_ids:
        member = AuditTeam(audit_id=audit.id, auditor_id=auditor)
        db.add(member)

    db.commit()

    return {"message": "Audit created", "audit_id": audit.id}

@router.get("/list")
def list_audits(db: Session = Depends(get_company_db)):
    return db.query(Audit).all()

@router.get("/detail/{audit_id}")
def audit_detail(audit_id: int, db: Session = Depends(get_company_db)):
    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    team = db.query(AuditTeam).filter(AuditTeam.audit_id == audit_id).all()
    return { "audit": audit, "team": team }
