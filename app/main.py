from fastapi import FastAPI
from app.db.master import engine
from app.db.base_class import Base
from app.models.company import Company
from app.models.user import User
from app.api.company import router as company_router
from app.api.user import router as user_router
from app.api.auth import router as auth_router   # if auth exists
from app.api.site import router as site_router
from app.api.department import router as department_router
from app.api.audit import router as audit_router

app = FastAPI(title="SVARP Backend")
app.include_router(company_router)
app.include_router(user_router)
app.include_router(auth_router)

app.include_router(site_router)
app.include_router(department_router)
app.include_router(audit_router)

Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"message": "SVARP Backend Running"}
