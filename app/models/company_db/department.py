from sqlalchemy import Column, Integer, String
from app.db.base_class import Base

class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    site_id = Column(Integer)   # foreign key (simple for SQLite)
