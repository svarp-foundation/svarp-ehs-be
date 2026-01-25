from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True)
    audit_id = Column(Integer, ForeignKey("audits.id"), nullable=False)

    category = Column(String)       # Fire / Electrical / Chemical...
    type = Column(String)           # NC / Observation / OFI / Good Practice
    description = Column(String)

    likelihood = Column(Integer, default=1)
    severity = Column(Integer, default=1)
    risk_score = Column(Integer, default=1)

    area = Column(String, nullable=True)
    evidence = Column(String, nullable=True)  # store file path later

    status = Column(String, default="open") # open, in_progress, closed
    assigned_to_id = Column(Integer, nullable=True) # User ID from master DB
