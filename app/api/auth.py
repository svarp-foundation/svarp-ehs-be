from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.master import SessionLocal
from app.models.user import User
from app.schemas.user import UserLogin
from app.core.security import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])

def get_master_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_master_db)):
    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token_data = {
        "user_id": db_user.id,
        "company_id": db_user.company_id,
        "role": db_user.role
    }

    access_token = create_access_token(token_data)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": db_user.id,
        "company_id": db_user.company_id,
        "role": db_user.role
    }
