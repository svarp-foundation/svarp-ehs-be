from pydantic import BaseModel

class FindingCreate(BaseModel):
    audit_id: int
    category: str
    type: str
    description: str
    likelihood: int
    severity: int
    area: str | None = None
