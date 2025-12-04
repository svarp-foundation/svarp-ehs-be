from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.master import SessionLocal
from app.models.company import Company
from app.schemas.company import CompanyCreate
from app.db.init_company_db import create_company_database

router = APIRouter(prefix="/company", tags=["Company"])

def get_master_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/create")
def create_company(company: CompanyCreate, db: Session = Depends(get_master_db)):
    name = company.name

    if not name or name.strip() == "":
        raise HTTPException(status_code=400, detail="Company name is required")

    # 1️⃣ Check if company already exists
    existing = db.query(Company).filter(Company.name.ilike(name)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Company already exists")

    new_company = Company(name=company.name)
    db.add(new_company)
    db.commit()
    db.refresh(new_company)

    # Create company-specific DB
    db_path = create_company_database(new_company.id)
    new_company.db_path = db_path
    db.commit()

    return {
        "message": "Company created successfully",
        "company_id": new_company.id,
        "db_path": db_path
    }
