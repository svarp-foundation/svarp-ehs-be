from pydantic import BaseModel

class DepartmentCreate(BaseModel):
    name: str
    site_id: int