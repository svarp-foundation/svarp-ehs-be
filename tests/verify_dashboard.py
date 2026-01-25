
import sys
import os
from sqlalchemy import text
from fastapi.testclient import TestClient

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from app.main import app
from app.db.master import SessionLocal
from app.models.user import User
from app.core.security import create_access_token
from app.db.company_session import migrate_company_db
from app.db.db_session import get_company_engine
from sqlalchemy.orm import sessionmaker
from app.models.company_db.site import Site
from app.models.company_db.audit import Audit
from app.models.company_db.finding import Finding
from app.models.company_db.audit_team import AuditTeam

client = TestClient(app)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_company_app_db(company_id):
    migrate_company_db(company_id)
    db_path = f"tmp/ehs_db/company_{company_id}.db"
    engine = get_company_engine(db_path)
    Session = sessionmaker(bind=engine)
    return Session()

def test_dashboard_stats():
    db = next(get_db())
    cid = 304 # Dashboard Test CID
    
    # 1. Setup Admin & Auditor
    email_admin = "dash_admin@test.com"
    email_auditor = "dash_auditor@test.com"
    
    db.query(User).filter(User.email.in_([email_admin, email_auditor])).delete()
    db.commit()
    
    admin = User(name="D Admin", email=email_admin, password="pwd", role="admin", company_id=cid)
    auditor = User(name="D Auditor", email=email_auditor, password="pwd", role="auditor", company_id=cid)
    db.add(admin)
    db.add(auditor)
    db.commit()
    
    token_admin = create_access_token({"sub": email_admin, "role": "admin", "company_id": cid, "user_id": admin.id})
    token_auditor = create_access_token({"sub": email_auditor, "role": "auditor", "company_id": cid, "user_id": auditor.id})
    auth_admin = {"Authorization": f"Bearer {token_admin}"}
    auth_auditor = {"Authorization": f"Bearer {token_auditor}"}
    
    # Clean DB
    cdb = get_company_app_db(cid)
    # Ensure tables exist (migration handles creation if missing, but just in case)
    from app.db.base_class import Base
    from app.db.db_session import get_company_engine
    
    # Actually get_company_app_db already calls migrate_company_db, which creates tables. 
    # But if verify_dashboard run on fresh DB, tables are empty anyway.
    # The error "no such table: audit_teams" implies migration didn't run or table name wrong.
    # In my model it is 'audit_teams'.
    # Let's inspect what happened.
    # Actually, migrate_company_db creates tables if DB not exists.
    # The error occurred at 'DELETE FROM audit_teams'.
    # Maybe migrate didn't create it? 
    # Ah, the models must be imported in auto_migrate.py for metadata.create_all to work!
    # Let's check auto_migrate.py imports.
    
    try:
        cdb.execute(text("DELETE FROM audit_teams"))
    except Exception:
        pass # Table might not exist yet if fresh, which is fine
        
    try:
        cdb.execute(text("DELETE FROM findings"))
        cdb.execute(text("DELETE FROM audits"))
        cdb.execute(text("DELETE FROM sites"))
        cdb.commit()
    except Exception:
        pass
    
    print("\n[TEST] Starting Dashboard Verification")

    # 2. Setup Data
    # Site 1
    s1 = Site(name="Site D1", location="Loc D1")
    cdb.add(s1)
    cdb.flush()
    cdb.refresh(s1)
    
    # Audit 1 (In Progress)
    a1 = Audit(title="Audit 1", audit_type="Int", site_id=s1.id, status="in_progress")
    cdb.add(a1)
    cdb.flush()
    
    # Findings for A1 (assigned to Auditor)
    f1 = Finding(audit_id=a1.id, category="Safety", type="NC", description="F1", likelihood=5, severity=5, risk_score=25, status="open", assigned_to_id=auditor.id)
    cdb.add(f1)
    
    # Audit 2 (Completed) - Not assigned to Auditor
    a2 = Audit(title="Audit 2", audit_type="Ext", site_id=s1.id, status="completed")
    cdb.add(a2)
    cdb.flush()
    
    # Findings for A2 (Unassigned)
    f2 = Finding(audit_id=a2.id, category="Env", type="OFI", description="F2", likelihood=1, severity=1, risk_score=1, status="closed")
    cdb.add(f2)
    
    # Audit 3 (Planned) - Assigned to Auditor
    a3 = Audit(title="Audit 3", audit_type="Int", site_id=s1.id, status="planned")
    cdb.add(a3)
    cdb.flush()
    
    # Assign Auditor to A1 and A3
    t1 = AuditTeam(audit_id=a1.id, auditor_id=auditor.id)
    t3 = AuditTeam(audit_id=a3.id, auditor_id=auditor.id)
    cdb.add(t1)
    cdb.add(t3)
    
    cdb.commit()
    print("[SUCCESS] Data Setup Complete")

    # 3. Test ADMIN Stats (Global)
    res = client.get("/dashboard/stats", headers=auth_admin)
    assert res.status_code == 200
    stats = res.json()
    
    assert stats["audits"]["total"] == 3
    assert stats["audits"]["by_status"].get("in_progress") == 1
    assert stats["audits"]["by_status"].get("completed") == 1
    assert stats["findings"]["total"] == 2
    assert stats["findings"]["by_risk"].get("high") == 1
    assert stats["findings"]["by_risk"].get("low") == 1
    print("[SUCCESS] Admin stats verified (Global view)")

    # 4. Test AUDITOR Stats (Filtered)
    res = client.get("/dashboard/stats", headers=auth_auditor)
    assert res.status_code == 200
    stats = res.json()
    
    # Auditor is assigned to A1 and A3 (total 2 visible audits)
    assert stats["audits"]["total"] == 2
    assert stats["audits"]["by_status"].get("in_progress") == 1
    assert "completed" not in stats["audits"]["by_status"] or stats["audits"]["by_status"].get("completed") == 0
    
    # Visible Findings (From assigned audits A1 and A3) -> F1 belongs to A1. F2 belongs to A2 (not assigned).
    # Logic in dashboard.py: finding_q.filter(Audit.id.in_(assigned_audit_ids))
    # So F1 is visible. F2 is not.
    assert stats["findings"]["total"] == 1 
    
    # Pending Findings (Assigned to me directly)
    # F1 is assigned to Auditor. Status open.
    assert stats.get("my_pending_findings") == 1
    
    print("[SUCCESS] Auditor stats verified (Filtered view)")

    print("\nALL DASHBOARD TESTS PASSED")

if __name__ == "__main__":
    test_dashboard_stats()
