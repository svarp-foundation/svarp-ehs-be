from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.core.security import SECRET_KEY, ALGORITHM
from app.models.user import User
from app.db.master import SessionLocal

bearer_scheme = HTTPBearer()

def get_master_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: SessionLocal = Depends(get_master_db) # type: ignore
):
    # 🔥 FIX 1: Extract the real JWT token string
    jwt_token = token.credentials

    try:
        # 🔥 FIX 2: Decode using token string only
        payload = jwt.decode(jwt_token, SECRET_KEY, algorithms=[ALGORITHM])

        user_id = payload.get("user_id")
        company_id = payload.get("company_id")  # optional usage

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Fetch user from master DB
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user
