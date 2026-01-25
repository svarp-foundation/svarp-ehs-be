
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
from app.models.company_db.audit_log import AuditLog
from app.models.company_db.finding import Finding
from app.models.company_db.department import Department

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

def test_audit_lifecycle():
    db = next(get_db())
    cid = 302 # Application ID for this test
    
    # 1. Setup Admin
    email = "lifecycle@test.com"
    db.query(User).filter(User.email == email).delete()
    db.commit()
    admin = User(name="Audit Admin", email=email, password="pwd", role="admin", company_id=cid)
    db.add(admin)
    db.commit()
    
    token = create_access_token({"sub": email, "role": "admin", "company_id": cid, "user_id": admin.id})
    auth = {"Authorization": f"Bearer {token}"}
    
    # Ensure DB is migrated and clean
    cdb = get_company_app_db(cid)
    cdb.execute(text("DELETE FROM audit_logs"))
    cdb.execute(text("DELETE FROM findings"))
    cdb.execute(text("DELETE FROM audits"))
    cdb.execute(text("DELETE FROM sites"))
    cdb.commit()
    
    print("\n[TEST] Starting Audit Lifecycle Tests")

    # 2. Setup Site
    site = Site(name="Factory L", location="Lock City")
    cdb.add(site)
    cdb.commit()
    site_id = site.id
    
    # 3. Create Audit (Planned)
    res = client.post("/audit/create", json={
        "title": "Safety Audit 2026",
        "audit_type": "Internal",
        "site_id": site_id,
        "scope": "Full factory",
        "start_date": "2026-01-01T00:00:00",
        "end_date": "2026-01-05T00:00:00"
    }, headers=auth)
    assert res.status_code == 201
    audit_id = res.json()["audit_id"]
    print("[SUCCESS] Created Audit")
    
    # Verify Log
    logs = cdb.query(AuditLog).filter(AuditLog.target_id == audit_id).all()
    assert len(logs) > 0
    assert logs[0].action == "CREATE"
    print("[SUCCESS] Creation logged")

    # 4. Transitions
    # Planned -> In Progress
    res = client.patch(f"/audit/{audit_id}", json={"status": "in_progress"}, headers=auth)
    assert res.status_code == 200
    print("[SUCCESS] Transitioned to In Progress")
    
    # In Progress -> Completed
    res = client.patch(f"/audit/{audit_id}", json={"status": "completed"}, headers=auth)
    assert res.status_code == 200
    print("[SUCCESS] Transitioned to Completed")
    
    # Completed -> Locked
    res = client.patch(f"/audit/{audit_id}", json={"status": "locked"}, headers=auth)
    assert res.status_code == 200
    print("[SUCCESS] Transitioned to Locked")
    
    # Verify Logs
    logs = cdb.query(AuditLog).filter(AuditLog.target_id == audit_id, AuditLog.action == "STATUS_CHANGE").all()
    assert len(logs) == 3
    print("[SUCCESS] All status changes logged")

    # 5. Lock Enforcement - Edit Audit
    res = client.patch(f"/audit/{audit_id}", json={"title": "Hacked Title"}, headers=auth)
    assert res.status_code == 400
    assert "locked" in res.json()["detail"]
    print("[SUCCESS] Blocked editing locked audit")
    
    # 6. Lock Enforcement - Add Finding
    res = client.post("/finding/create", json={
        "audit_id": audit_id,
        "category": "Safety",
        "type": "NC",
        "description": "High Risk Found Here",
        "likelihood": 3,
        "severity": 3
    }, headers=auth)
    if res.status_code != 400:
        print(f"[FAIL] Expected 400, got {res.status_code}. Body: {res.text}")
        
        # Debug: Check audit status in DB
        aa = cdb.query(Audit).filter(Audit.id == audit_id).first()
        print(f"[DEBUG] Audit info in DB: id={aa.id}, status='{aa.status}'")
    
    assert res.status_code == 400
    assert "locked" in res.json()["detail"]
    print("[SUCCESS] Blocked adding finding to locked audit")
    
    # 7. Safe Delete Check (Locked)
    res = client.delete(f"/audit/{audit_id}", headers=auth)
    assert res.status_code == 400
    assert "locked" in res.json()["detail"]
    print("[SUCCESS] Blocked deleting locked audit")

    print("\nALL LIFECYCLE TESTS PASSED")

if __name__ == "__main__":
    test_audit_lifecycle()
