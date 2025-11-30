from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str
    company_id: int

class UserLogin(BaseModel):
    email: str
    password: str
