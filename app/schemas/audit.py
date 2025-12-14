# app/schemas/audit.py
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


# -------- CREATE --------
class AuditCreate(BaseModel):
    title: str
    audit_type: str
    site_id: int
    scope: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    checklist_id: Optional[int] = None
    auditor_ids: List[int] = []


# -------- UPDATE --------
class AuditUpdate(BaseModel):
    title: Optional[str] = None
    audit_type: Optional[str] = None
    site_id: Optional[int] = None
    scope: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    checklist_id: Optional[int] = None
    status: Optional[str] = None


# -------- RESPONSE --------
class AuditOut(BaseModel):
    id: int
    title: str
    audit_type: str
    site_id: int
    site_name: str | None = None
    scope: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    status: str | None = None
    checklist_id: Optional[int] = None  # ✅ FIX
    created_at: datetime | None = None

    class Config:
        from_attributes = True