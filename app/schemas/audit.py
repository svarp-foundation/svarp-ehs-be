from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class AuditCreate(BaseModel):
    title: str
    audit_type: str
    site_id: int
    scope: Optional[str] = None
    start_date: datetime
    end_date: datetime
    auditor_ids: List[int]
    checklist_id: Optional[int] = None
