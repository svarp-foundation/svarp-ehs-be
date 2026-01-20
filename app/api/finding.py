# app/api/finding.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict

from app.db.company_session import get_company_db
from app.models.company_db.finding import Finding
from app.models.company_db.audit import Audit
from app.models.company_db.audit_team import AuditTeam
from app.schemas.finding import FindingCreate, FindingOut, FindingUpdate
from app.core.dependencies import get_current_user
from app.core.permissions import require_admin, check_audit_access
from app.models.user import User

router = APIRouter(prefix="/finding", tags=["Findings"], dependencies=[Depends(get_current_user)])

# Allowed finding types
ALLOWED_TYPES = {"NC", "Observation", "OFI", "Good Practice"}


# --------------------------------------------------------------------------
# CREATE FINDING (Admin only)
# --------------------------------------------------------------------------
@router.post("/create", status_code=status.HTTP_201_CREATED, response_model=Dict)
def create_finding(
    payload: FindingCreate,
    _: User = Depends(require_admin),  # 🔒 Admin only
    db: Session = Depends(get_company_db)
):

    # Validate referenced audit exists
    audit = db.query(Audit).filter(Audit.id == payload.audit_id).first()
    if not audit:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid audit_id: audit does not exist")

    # Validate finding type
    if payload.finding_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
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
# 🔒 Auditors only see findings from assigned audits
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_company_db)
):
    query = db.query(Finding)

    # 🔒 For non-admins, filter to only assigned audits
    if current_user.role != "admin":
        assigned_audit_ids = db.query(AuditTeam.audit_id).filter(
            AuditTeam.auditor_id == current_user.id
        ).subquery()
        query = query.filter(Finding.audit_id.in_(assigned_audit_ids))

    if audit_id:
        # 🔒 Additional check: verify access to specific audit
        if not check_audit_access(current_user, audit_id, db):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Audit not found")  # 🔒 Hide existence
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
# 🔒 Verify access to the finding's audit
# --------------------------------------------------------------------------
@router.get("/{id}", response_model=FindingOut)
def get_finding(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_company_db)
):
    f = db.query(Finding).filter(Finding.id == id).first()
    if not f:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Finding not found")

    # 🔒 Verify access to the finding's audit
    if not check_audit_access(current_user, f.audit_id, db):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Finding not found")  # 🔒 Hide existence

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
# 🔒 Verify assignment before returning findings
# --------------------------------------------------------------------------
@router.get("/by-audit/{audit_id}", response_model=List[FindingOut])
def get_findings_by_audit(
    audit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_company_db)
):

    audit = db.query(Audit).filter(Audit.id == audit_id).first()
    if not audit:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid audit_id")

    # 🔒 Verify access to this audit
    if not check_audit_access(current_user, audit_id, db):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Audit not found")  # 🔒 Hide existence

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
# UPDATE FINDING (Admin only)
# --------------------------------------------------------------------------
@router.patch("/{id}", response_model=Dict)
def update_finding(
    id: int,
    payload: FindingUpdate,
    _: User = Depends(require_admin),  # 🔒 Admin only
    db: Session = Depends(get_company_db)
):
    f = db.query(Finding).filter(Finding.id == id).first()
    if not f:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Finding not found")

    # Validate & update
    if payload.finding_type:
        if payload.finding_type not in ALLOWED_TYPES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid type. Allowed: {', '.join(ALLOWED_TYPES)}")
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
# DELETE FINDING (Admin only)
# --------------------------------------------------------------------------
@router.delete("/{id}", response_model=Dict)
def delete_finding(
    id: int,
    _: User = Depends(require_admin),  # 🔒 Admin only
    db: Session = Depends(get_company_db)
):
    f = db.query(Finding).filter(Finding.id == id).first()
    if not f:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Finding not found")

    db.delete(f)
    db.commit()

    return {"message": "Finding deleted", "id": id}
