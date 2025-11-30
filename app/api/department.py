from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.department import DepartmentCreate
from app.models.company_db.department import Department
from app.db.company_session import get_company_db

router = APIRouter(prefix="/department", tags=["Department"])

@router.post("/create")
def create_department(data: DepartmentCreate, db: Session = Depends(get_company_db)):
    new_dep = Department(name=data.name, site_id=data.site_id)
    db.add(new_dep)
    db.commit()
    db.refresh(new_dep)
    return {"message": "Department created", "id": new_dep.id}

@router.get("/all")
def get_departments(db: Session = Depends(get_company_db)):
    return db.query(Department).all()
