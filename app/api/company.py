from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.master import SessionLocal
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyCreate
from app.db.init_company_db import create_company_database
from app.core.security import hash_password

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

    # 2️⃣ Check if admin email already exists (globally)
    existing_user = db.query(User).filter(User.email == company.admin_email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Admin email already registered")

    # 3️⃣ Create Company
    new_company = Company(name=company.name)
    db.add(new_company)
    db.commit()
    db.refresh(new_company)

    # 4️⃣ Create Admin User
    admin_user = User(
        name=company.admin_name,
        email=company.admin_email,
        password=hash_password(company.admin_password),
        role="admin",
        company_id=new_company.id
    )
    db.add(admin_user)
    db.commit()

    # 5️⃣ Create company-specific DB
    db_path = create_company_database(new_company.id)
    new_company.db_path = db_path
    db.commit()

    return {
        "message": "Company and Admin created successfully",
        "company_id": new_company.id,
        "admin_id": admin_user.id,
        "db_path": db_path
    }
