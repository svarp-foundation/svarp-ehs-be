# app/schemas/finding.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class FindingCreate(BaseModel):
    audit_id: int = Field(..., gt=0)
    category: str = Field(..., min_length=1)
    finding_type: str = Field(..., alias="type")
    description: str = Field(..., min_length=5)
    likelihood: int = Field(..., ge=1, le=5)
    severity: int = Field(..., ge=1, le=5)
    area: Optional[str] = None

    model_config = {
        "validate_by_name": True
    }


class FindingUpdate(BaseModel):
    category: Optional[str] = None
    finding_type: Optional[str] = Field(None, alias="type")
    description: Optional[str] = None
    likelihood: Optional[int] = Field(None, ge=1, le=5)
    severity: Optional[int] = Field(None, ge=1, le=5)
    area: Optional[str] = None

    model_config = {
        "validate_by_name": True
    }


class FindingOut(BaseModel):
    id: int
    audit_id: int
    audit_title: Optional[str] = None
    category: str
    type: str
    description: str
    likelihood: int
    severity: int
    risk_score: int
    area: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }