from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.company_session import get_company_db
from app.models.company_db.site import Site
from app.models.company_db.department import Department
from app.models.company_db.audit import Audit
from app.models.company_db.finding import Finding

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats")
def dashboard_stats(db: Session = Depends(get_company_db)):
    return {
        "sites": db.query(Site).count(),
        "departments": db.query(Department).count(),
        "audits": db.query(Audit).count(),
        "findings": db.query(Finding).count(),
    }
