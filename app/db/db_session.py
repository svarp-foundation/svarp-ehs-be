from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def get_company_engine(db_path: str):
    return create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False}
    )

def get_company_session(db_path: str):
    engine = get_company_engine(db_path)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
