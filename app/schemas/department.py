from pydantic import BaseModel

class DepartmentCreate(BaseModel):
    name: str
    site_id: int

class DepartmentResponse(DepartmentCreate):
    id: int
    has_findings: bool

    class Config:
        from_attributes = True