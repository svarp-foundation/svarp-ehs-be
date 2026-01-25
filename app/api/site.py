from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.schemas.site import SiteCreate
from app.models.company_db.site import Site
from app.models.company_db.audit import Audit
from app.models.company_db.audit_log import AuditLog
from app.models.company_db.department import Department
from app.db.company_session import get_company_db
from app.core.dependencies import get_current_user
from app.core.permissions import require_admin
from app.models.user import User

router = APIRouter(prefix="/site", tags=["Site"], dependencies=[Depends(get_current_user)])

@router.post("/create")
def create_site(
    data: SiteCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_company_db)
):
    new_site = Site(name=data.name, location=data.location, is_active=1)
    db.add(new_site)
    db.commit()
    db.refresh(new_site)

    # [NEW] Audit Log
    log = AuditLog(
        action="CREATE",
        target_type="SITE",
        target_id=new_site.id,
        actor_id=admin.id,
        details=f"Created site {new_site.name}"
    )
    db.add(log)
    db.commit()

    return {"message": "Site created", "id": new_site.id}

@router.get("/all")
def get_sites(db: Session = Depends(get_company_db)):
    # Return sites with active status + audit count
    # Logic: Left join audits -> count
    results = (
        db.query(Site, func.count(Audit.id).label("audit_count"))
        .outerjoin(Audit, (Audit.site_id == Site.id) & (Audit.status != "cancelled")) # Optional: filter cancelled
        .filter(Site.is_active == 1)
        .group_by(Site.id)
        .all()
    )
    
    return [
        {
            "id": s.id,
            "name": s.name,
            "location": s.location,
            "audit_count": count
        }
        for s, count in results
    ]


@router.delete("/{site_id}")
def delete_site(
    site_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_company_db)
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Site not found")

    # 🔒 Check dependencies: Audits
    if db.query(Audit).filter(Audit.site_id == site_id).count() > 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete site with existing audits")
        
    # 🔒 Check dependencies: Departments (Soft check? Or strictly block?)
    # If departments exist, we should probably block too, or cascade soft delete?
    # For now, block to be safe.
    if db.query(Department).filter(Department.site_id == site_id).count() > 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete site with sub-departments")

    # Soft Delete
    site.is_active = 0
    
    # Audit Log
    log = AuditLog(
        action="DELETE",
        target_type="SITE",
        target_id=site_id,
        actor_id=admin.id,
        details=f"Soft deleted site {site.name}"
    )
    db.add(log)
    
    db.commit()
    return {"message": "Site deleted"}
