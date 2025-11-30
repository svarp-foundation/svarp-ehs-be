from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.finding import FindingCreate
from app.models.company_db.finding import Finding
from app.models.company_db.audit import Audit
from app.db.company_session import get_company_db

router = APIRouter(prefix="/finding", tags=["Findings"])

@router.post("/create")
def create_finding(data: FindingCreate, db: Session = Depends(get_company_db)):

    # Validate audit
    audit = db.query(Audit).filter(Audit.id == data.audit_id).first()
    if not audit:
        raise HTTPException(400, "Invalid audit_id")

    # Risk Score
    risk = data.likelihood * data.severity

    new_finding = Finding(
        audit_id=data.audit_id,
        category=data.category,
        type=data.type,
        description=data.description,
        likelihood=data.likelihood,
        severity=data.severity,
        risk_score=risk,
        area=data.area
    )

    db.add(new_finding)
    db.commit()
    db.refresh(new_finding)

    return {"message": "Finding added", "id": new_finding.id}

@router.get("/list/{audit_id}")
def list_findings(audit_id: int, db: Session = Depends(get_company_db)):
    return db.query(Finding).filter(Finding.audit_id == audit_id).all()

