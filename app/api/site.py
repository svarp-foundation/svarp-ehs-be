from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.site import SiteCreate
from app.models.company_db.site import Site
from app.db.company_session import get_company_db
from app.core.dependencies import get_current_user
from app.core.permissions import require_admin
from app.models.user import User

router = APIRouter(prefix="/site", tags=["Site"], dependencies=[Depends(get_current_user)])

@router.post("/create")
def create_site(
    data: SiteCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_company_db)
):
    new_site = Site(name=data.name, location=data.location)
    db.add(new_site)
    db.commit()
    db.refresh(new_site)
    return {"message": "Site created", "id": new_site.id}

@router.get("/all")
def get_sites(db: Session = Depends(get_company_db)):
    return db.query(Site).all()


@router.delete("/{site_id}")
def delete_site(
    site_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_company_db)
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Site not found")

    # 🔒 Check dependencies: Audits
    from app.models.company_db.audit import Audit
    if db.query(Audit).filter(Audit.site_id == site_id).count() > 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete site with existing audits")
        
    # 🔒 Check dependencies: Departments
    from app.models.company_db.department import Department
    if db.query(Department).filter(Department.site_id == site_id).count() > 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete site with sub-departments")

    db.delete(site)
    db.commit()
    return {"message": "Site deleted"}
