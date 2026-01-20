from sqlalchemy import Column, Integer, UniqueConstraint
from app.db.base_class import Base

class AuditTeam(Base):
    __tablename__ = "audit_team"
    __table_args__ = (
        UniqueConstraint('audit_id', 'auditor_id', name='uq_audit_auditor'),
    )

    id = Column(Integer, primary_key=True)
    audit_id = Column(Integer, nullable=False)
    auditor_id = Column(Integer, nullable=False)
