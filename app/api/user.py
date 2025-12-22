from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.master import SessionLocal
from app.models.user import User
from app.models.company import Company
from app.schemas.user import UserCreate
from app.core.security import hash_password
from app.schemas.user import UserUpdate
from app.models.company_db.audit_team import AuditTeam

router = APIRouter(prefix="/user", tags=["User"])

def get_master_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/create")
def create_user(user: UserCreate, db: Session = Depends(get_master_db)):
    company = db.query(Company).filter(Company.id == user.company_id).first()
    if not company:
        raise HTTPException(status_code=400, detail="Company does not exist")

    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    new_user = User(
        name=user.name,
        email=user.email,
        password=hash_password(user.password),
        role=user.role,
        company_id=user.company_id
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created", "user_id": new_user.id}


@router.get("/list")
def list_users(
    role: str | None = None,
    company_id: int | None = None,
    db: Session = Depends(get_master_db)
):
    q = db.query(User)

    if company_id:
        q = q.filter(User.company_id == company_id)

    if role:
        q = q.filter(User.role == role)

    return q.all()



@router.get("/auditors")
def list_auditors(company_id: int, db: Session = Depends(get_master_db)):
    return db.query(User)\
        .filter(User.company_id == company_id)\
        .filter(User.role == "auditor")\
        .all()


@router.put("/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_master_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # update allowed fields only
    if payload.name is not None:
        user.name = payload.name

    if payload.role is not None:
        user.role = payload.role

    if payload.password:
        user.password = hash_password(payload.password)

    db.commit()
    db.refresh(user)

    return {
        "message": "User updated",
        "user_id": user.id
    }


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_master_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 🚫 Block if user is assigned to any audit
    assigned = db.query(AuditTeam).filter(
        AuditTeam.auditor_id == user_id
    ).count()

    if assigned > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete user assigned to audits"
        )

    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully"}

