from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.master import SessionLocal
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import hash_password

router = APIRouter(prefix="/user", tags=["User"])

def get_master_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/create")
def create_user(user: UserCreate, db: Session = Depends(get_master_db)):
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
