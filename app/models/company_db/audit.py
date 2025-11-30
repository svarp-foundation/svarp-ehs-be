from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base_class import Base

class Audit(Base):
    __tablename__ = "audits"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    audit_type = Column(String)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)
    scope = Column(String)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    status = Column(String, default="planned")  # planned, in-progress, completed
    checklist_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
