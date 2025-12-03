import os
from app.db.base_class import Base
from app.db.db_session import get_company_engine
from app.models.company_db.site import Site
from app.models.company_db.department import Department
from app.models.company_db.audit import Audit
from app.models.company_db.audit_team import AuditTeam

def create_company_database(company_id: int):
    db_path = f"tmp/ehs_db/company_{company_id}.db"

    if not os.path.exists("db"):
        os.makedirs("db")

    engine = get_company_engine(db_path)
    Base.metadata.create_all(bind=engine)

    return db_path
