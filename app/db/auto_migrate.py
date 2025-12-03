import os
from sqlalchemy import inspect
from app.db.db_session import get_company_engine
from app.db.base_class import Base

from app.models.company_db.site import Site
from app.models.company_db.department import Department
from app.models.company_db.audit import Audit
from app.models.company_db.audit_team import AuditTeam
from app.models.company_db.finding import Finding

def migrate_company_db(company_id: int):
    db_path = f"tmp/ehs_db/company_{company_id}.db"

    if not os.path.exists(db_path):
        print(f"[MIGRATION] DB {db_path} not found. Creating fresh DB.")
        engine = get_company_engine(db_path)
        Base.metadata.create_all(bind=engine)
        return

    engine = get_company_engine(db_path)
    inspector = inspect(engine)

    existing_tables = inspector.get_table_names()
    defined_tables = Base.metadata.tables.keys()

    missing_tables = [t for t in defined_tables if t not in existing_tables]

    if missing_tables:
        print(f"[MIGRATION] Missing tables for company {company_id}: {missing_tables}")
        Base.metadata.create_all(bind=engine)
        print("[MIGRATION] Migration complete.")
    else:
        print(f"[MIGRATION] No missing tables for company {company_id}. DB is up-to-date.")
