import os
from sqlalchemy import inspect, text
from app.db.db_session import get_company_engine
from app.db.base_class import Base

from app.models.company_db.site import Site
from app.models.company_db.department import Department
from app.models.company_db.audit import Audit
from app.models.company_db.audit_team import AuditTeam
from app.models.company_db.finding import Finding
from app.models.company_db.audit_log import AuditLog

from app.core.config import settings

def migrate_company_db(company_id: int):
    db_path = settings.get_company_db_path(company_id)

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
        # Check for schema updates (e.g. new columns)
        # Simple manual migration for 'is_active' on 'sites'
        if "sites" in existing_tables:
            columns = [c["name"] for c in inspector.get_columns("sites")]
            if "is_active" not in columns:
                print(f"[MIGRATION] Adding 'is_active' column to sites for company {company_id}")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE sites ADD COLUMN is_active INTEGER DEFAULT 1"))
                    conn.execute(text("ALTER TABLE sites ADD COLUMN is_active INTEGER DEFAULT 1"))
                    conn.commit()
        
        if "findings" in existing_tables:
            columns = [c["name"] for c in inspector.get_columns("findings")]
            if "status" not in columns:
                print(f"[MIGRATION] Adding 'status' and 'assigned_to_id' to findings for company {company_id}")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE findings ADD COLUMN status VARCHAR DEFAULT 'open'"))
                    conn.execute(text("ALTER TABLE findings ADD COLUMN assigned_to_id INTEGER"))
                    conn.commit()

        print(f"[MIGRATION] DB Check complete for company {company_id}.")
