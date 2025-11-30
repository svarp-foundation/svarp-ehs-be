from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.department import DepartmentCreate
from app.models.company_db.department import Department
from app.db.company_session import get_company_db
from app.models.company_db.site import Site

router = APIRouter(prefix="/department", tags=["Department"])

@router.post("/create")
def create_department(data: DepartmentCreate, db: Session = Depends(get_company_db)):

    # 🔥 Validate site existence
    site = db.query(Site).filter(Site.id == data.site_id).first()
    if not site:
        raise HTTPException(status_code=400, detail="Invalid site_id: Site does not exist")

    new_dep = Department(
        name=data.name,
        site_id=data.site_id
    )

    db.add(new_dep)
    db.commit()
    db.refresh(new_dep)

    return {"message": "Department created", "id": new_dep.id}

@router.get("/all")
def get_departments(db: Session = Depends(get_company_db)):
    return db.query(Department).all()
