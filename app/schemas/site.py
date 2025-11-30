from pydantic import BaseModel

class SiteCreate(BaseModel):
    name: str
    location: str | None = None
