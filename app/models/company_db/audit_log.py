import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from app.db.base_class import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String)  # CREATE, UPDATE, DELETE
    target_type = Column(String)  # USER, AUDIT, etc.
    target_id = Column(Integer)  # ID of the affected entity
    actor_id = Column(Integer)  # ID of the user performing the action
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    details = Column(Text, nullable=True)  # JSON or text description of changes
