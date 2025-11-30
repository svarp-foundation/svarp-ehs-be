from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.base_class import Base

class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)   # foreign key (simple for SQLite)
