from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.master import SessionLocal
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import hash_password
from app.core.permissions import require_admin
from app.core.dependencies import get_current_user
from app.models.company_db.audit_team import AuditTeam
from app.db.company_session import get_company_db

router = APIRouter(prefix="/user", tags=["User"])


def get_master_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------- CREATE USER --------------------
@router.post("/create")
def create_user(
    user: UserCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_master_db)
):
    new_user = User(
        name=user.name,
        email=user.email,
        password=hash_password(user.password),
        role=user.role,
        company_id=admin.company_id  # 🔥 Enforce Admin's Company
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created", "user_id": new_user.id}


# -------------------- LIST USERS (FIXED) --------------------
@router.get("/list")
def list_users(
    role: str | None = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_master_db)
):
    q = db.query(User).filter(User.company_id == admin.company_id) # 🔥 Enforce Isolation

    if role:
        q = q.filter(User.role == role)

    return q.all()


# -------------------- UPDATE USER --------------------
@router.put("/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_master_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    if user.company_id != admin.company_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")  # 🔒 Hide existence

    if payload.name is not None:
        user.name = payload.name
    if payload.role is not None:
        user.role = payload.role
    if payload.password:
        user.password = hash_password(payload.password)

    db.commit()
    return {"message": "User updated"}


# -------------------- DELETE USER (SAFE) --------------------
@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_master_db),
    company_db: Session = Depends(get_company_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    if user.company_id != admin.company_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")  # 🔒 Hide existence

    assigned = company_db.query(AuditTeam).filter(
        AuditTeam.auditor_id == user_id
    ).count()

    if assigned > 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete user assigned to audits")

    db.delete(user)
    db.commit()
    return {"message": "User deleted"}
