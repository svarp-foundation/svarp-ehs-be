import os
from app.db.base_class import Base
from app.db.db_session import get_company_engine
from app.models.company_db.site import Site
from app.models.company_db.department import Department
from app.models.company_db.audit import Audit
from app.models.company_db.audit_team import AuditTeam

from app.core.config import settings

def create_company_database(company_id: int):
    db_path = settings.get_company_db_path(company_id)
    
    # Ensure directory exists
    dir_name = os.path.dirname(db_path)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

    engine = get_company_engine(db_path)
    Base.metadata.create_all(bind=engine)

    return db_path
