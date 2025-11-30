from sqlalchemy.orm import sessionmaker
from app.db.db_session import get_company_engine
from app.core.auth import get_current_user
from app.db.auto_migrate import migrate_company_db
from fastapi import Depends

def get_company_db(current_user=Depends(get_current_user)):
    company_id = current_user.company_id
    db_path = f"db/company_{company_id}.db"

    migrate_company_db(company_id)
    engine = get_company_engine(db_path)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        yield db
    finally:
        db.close()
