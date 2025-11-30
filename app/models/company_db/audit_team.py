from sqlalchemy import Column, Integer, ForeignKey
from app.db.base_class import Base

class AuditTeam(Base):
    __tablename__ = "audit_team"

    id = Column(Integer, primary_key=True)
    audit_id = Column(Integer)
    auditor_id = Column(Integer)
