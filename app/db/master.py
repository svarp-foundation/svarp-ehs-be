from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

MASTER_DB_PATH = "tmp/ehs_db/master.db"

engine = create_engine(
    f"sqlite:///{MASTER_DB_PATH}",
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
