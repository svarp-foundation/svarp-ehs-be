from pydantic import BaseModel

class CompanyCreate(BaseModel):
    name: str
    admin_name: str
    admin_email: str
    admin_password: str
