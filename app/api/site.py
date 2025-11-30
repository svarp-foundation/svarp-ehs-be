from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.site import SiteCreate
from app.models.company_db.site import Site
from app.db.company_session import get_company_db

router = APIRouter(prefix="/site", tags=["Site"])

@router.post("/create")
def create_site(data: SiteCreate, db: Session = Depends(get_company_db)):
    new_site = Site(name=data.name, location=data.location)
    db.add(new_site)
    db.commit()
    db.refresh(new_site)
    return {"message": "Site created", "id": new_site.id}

@router.get("/all")
def get_sites(db: Session = Depends(get_company_db)):
    return db.query(Site).all()
