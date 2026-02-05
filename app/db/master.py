from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
import os

# Ensure the database directory exists
if not os.path.exists(settings.DATABASE_DIR):
    os.makedirs(settings.DATABASE_DIR)

engine = create_engine(
    settings.MASTER_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
