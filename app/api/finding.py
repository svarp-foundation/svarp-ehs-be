# app/api/finding.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict

from app.db.company_session import get_company_db
from app.models.company_db.finding import Finding
from app.models.company_db.audit import Audit
from app.schemas.finding import FindingCreate, FindingOut, FindingUpdate

router = APIRouter(prefix="/finding", tags=["Findings"])

# Allowed finding types
ALLOWED_TYPES = {"NC", "Observation", "OFI", "Good Practice"}


# --------------------------------------------------------------------------
# CREATE FINDING
# --------------------------------------------------------------------------
@router.post("/create", status_code=status.HTTP_201_CREATED, response_model=Dict)
def create_finding(payload: FindingCreate, db: Session = Depends(get_company_db)):

    # Validate referenced audit exists
    audit = db.query(Audit).filter(Audit.id == payload.audit_id).first()
    if not audit:
        raise HTTPException(status_code=400, detail="Invalid audit_id: audit does not exist")

    # Validate finding type
    if payload.finding_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid finding_type. Allowed: {', '.join(ALLOWED_TYPES)}"
        )

    # Risk score calculation
    risk_score = int(payload.likelihood) * int(payload.severity)

    new = Finding(
        audit_id=payload.audit_id,
        category=payload.category,
        type=payload.finding_type,
        description=payload.description,
        likelihood=payload.likelihood,
        severity=payload.severity,
        risk_score=risk_score,
        area=payload.area
    )

    db.add(new)
    db.commit()
    db.refresh(new)

    return {"message": "Finding added", "id": new.id}


# --------------------------------------------------------------------------
# GET ALL FINDINGS (PAGINATED + FILTERS)
# FIXED ROUTE → `/finding/get-all`
# --------------------------------------------------------------------------
@router.get("/get-all", response_model=List[FindingOut])
def list_findings(
    q: Optional[str] = Query(None),
    audit_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    finding_type: Optional[str] = Query(None),
    min_risk: Optional[int] = Query(None),
    max_risk: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_company_db)
):
    query = db.query(Finding)

    if audit_id:
        query = query.filter(Finding.audit_id == audit_id)
    if category:
        query = query.filter(Finding.category.ilike(f"%{category}%"))
    if finding_type:
        query = query.filter(Finding.type == finding_type)
    if q:
        query = query.filter(Finding.description.ilike(f"%{q}%"))
    if min_risk is not None:
        query = query.filter(Finding.risk_score >= min_risk)
    if max_risk is not None:
        query = query.filter(Finding.risk_score <= max_risk)

    rows = query.order_by(Finding.id.desc()).limit(limit).offset(offset).all()

    result = []
    for r in rows:
        audit = db.query(Audit).filter(Audit.id == r.audit_id).first()
        result.append({
            "id": r.id,
            "audit_id": r.audit_id,
            "audit_title": audit.title if audit else None,
            "category": r.category,
            "type": r.type,
            "description": r.description,
            "likelihood": r.likelihood,
            "severity": r.severity,
            "risk_score": r.risk_score,
            "area": r.area,
            "created_at": r.created_at.isoformat() if getattr(r, "created_at", None) else None
        })

    return result


# --------------------------------------------------------------------------
# GET SINGLE FINDING BY ID
# --------------------------------------------------------------------------
@router.get("/{id}", response_model=FindingOut)
def get_finding(id: int, db: Session = Depends(get_company_db)):
    f = db.query(Finding).filter(Finding.id == id).first()
    if not f:
        raise HTTPException(404, "Finding not found")

    audit = db.query(Audit).filter(Audit.id == f.audit_id).first()

    return {
        "id": f.id,
        "audit_id": f.audit_id,
        "audit_title": audit.title if audit else None,
        "category": f.category,
        "type": f.type,
        "description": f.description,
        "likelihood": f.likelihood,
        "severity": f.severity,
        "risk_score": f.risk_score,
        "area": f.area,
        "created_at": f.created_at.isoformat() if getattr(f, "created_at", None) else None
    }


# --------------------------------------------------------------------------
# GET FINDINGS BY AUDIT
# --------------------------------------------------------------------------
@router.get("/by-audit/{audit_id}", response_model=List[FindingOut])
def get_findings_by_audit(audit_id: int, db: Session = Depends(get_company_db)):

    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        raise HTTPException(400, "Invalid audit_id")

    rows = db.query(Finding).filter(Finding.audit_id == audit_id).order_by(Finding.id.desc()).all()

    result = []
    for r in rows:
        result.append({
            "id": r.id,
            "audit_id": r.audit_id,
            "audit_title": audit.title,
            "category": r.category,
            "type": r.type,
            "description": r.description,
            "likelihood": r.likelihood,
            "severity": r.severity,
            "risk_score": r.risk_score,
            "area": r.area,
            "created_at": r.created_at.isoformat() if getattr(r, "created_at", None) else None
        })

    return result


# --------------------------------------------------------------------------
# UPDATE FINDING
# --------------------------------------------------------------------------
@router.patch("/{id}", response_model=Dict)
def update_finding(id: int, payload: FindingUpdate, db: Session = Depends(get_company_db)):
    f = db.query(Finding).filter(Finding.id == id).first()
    if not f:
        raise HTTPException(404, "Finding not found")

    # Validate & update
    if payload.finding_type:
        if payload.finding_type not in ALLOWED_TYPES:
            raise HTTPException(400, f"Invalid type. Allowed: {', '.join(ALLOWED_TYPES)}")
        f.type = payload.finding_type

    if payload.category is not None:
        f.category = payload.category

    if payload.description is not None:
        f.description = payload.description

    if payload.area is not None:
        f.area = payload.area

    # If either value is changed — recalc risk
    if payload.likelihood is not None:
        f.likelihood = payload.likelihood
    if payload.severity is not None:
        f.severity = payload.severity

    f.risk_score = int(f.likelihood) * int(f.severity)

    db.commit()
    db.refresh(f)

    return {"message": "Finding updated", "id": f.id}


# --------------------------------------------------------------------------
# DELETE FINDING
# --------------------------------------------------------------------------
@router.delete("/{id}", response_model=Dict)
def delete_finding(id: int, db: Session = Depends(get_company_db)):
    f = db.query(Finding).filter(Finding.id == id).first()
    if not f:
        raise HTTPException(404, "Finding not found")

    db.delete(f)
    db.commit()

    return {"message": "Finding deleted", "id": id}
