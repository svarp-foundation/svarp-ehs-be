
import sys
import os
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from sqlalchemy import text

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

def test_site_management():
    db = next(get_db())
    cid = 300
    
    # 1. Setup Admin
    email = "site_admin@test.com"
    db.query(User).filter(User.email == email).delete()
    db.commit()
    admin = User(name="Site Admin", email=email, password="pwd", role="admin", company_id=cid)
    db.add(admin)
    db.commit()
    
    # Setup Auditor
    auditor_email = "site_auditor@test.com"
    db.query(User).filter(User.email == auditor_email).delete()
    db.commit()
    auditor = User(name="Site Auditor", email=auditor_email, password="pwd", role="auditor", company_id=cid)
    db.add(auditor)
    db.commit()
    
    
    token = create_access_token({"sub": email, "role": "admin", "company_id": cid, "user_id": admin.id})
    auth = {"Authorization": f"Bearer {token}"}
    
    token_aud = create_access_token({"sub": auditor_email, "role": "auditor", "company_id": cid, "user_id": auditor.id})
    auth_aud = {"Authorization": f"Bearer {token_aud}"}

    # Ensure DB is migrated (adds is_active)
    cdb = get_company_app_db(cid)
    # create clean slate
    cdb.execute(text("DELETE FROM sites"))
    cdb.execute(text("DELETE FROM audit_logs"))
    cdb.commit()
    
    print("\n[TEST] Starting Site Management Tests")

    # 2. Test Create Site (Admin)
    res = client.post("/site/create", json={"name": "Factory A", "location": "NY"}, headers=auth)
    assert res.status_code == 200
    site_id = res.json()["id"]
    print("[SUCCESS] Admin created site")

    # 3. Test Create Site (Auditor) -> Fail
    res = client.post("/site/create", json={"name": "HACKED"}, headers=auth_aud)
    assert res.status_code == 403
    print("[SUCCESS] Auditor blocked from creating site")

    # 4. Test Get Sites (List + Usage)
    res = client.get("/site/all", headers=auth)
    assert res.status_code == 200
    sites = res.json()
    assert len(sites) == 1
    assert sites[0]["audit_count"] == 0
    print("[SUCCESS] Site list returns audit_count")

    # 5. Test Soft Delete (No Audits)
    res = client.delete(f"/site/{site_id}", headers=auth)
    assert res.status_code == 200
    print("[SUCCESS] Admin deleted unused site")

    # Verify Logic: Site should still exist in DB but is_active=0
    site_obj = cdb.query(Site).filter(Site.id == site_id).first()
    assert site_obj is not None
    assert site_obj.is_active == 0
    print("[SUCCESS] Site verified as Soft Deleted in DB")

    # Verify not in List
    res = client.get("/site/all", headers=auth)
    assert len(res.json()) == 0
    print("[SUCCESS] Soft deleted site hidden from API list")

    # Re-activate for dependency test (or create new)
    site_obj.is_active = 1
    cdb.commit()
    
    # 6. Test Block Delete if Audits Exist
    # Create Audit manually in DB
    from app.models.company_db.audit import Audit
    audit = Audit(title="Test Audit", audit_type="Internal", site_id=site_id, status="planned")
    cdb.add(audit)
    cdb.commit()

    res = client.delete(f"/site/{site_id}", headers=auth)
    assert res.status_code == 400
    assert "existing audits" in res.json()["detail"]
    print("[SUCCESS] Blocked deletion of site with audits")

    # 7. Verify Audit Log
    # We expect 1 create and 1 delete log
    from app.models.company_db.audit_log import AuditLog
    logs = cdb.query(AuditLog).filter(AuditLog.target_type == "SITE").all()
    assert len(logs) >= 2 # Create + Delete
    print(f"[SUCCESS] Audit logs found: {len(logs)}")

    print("\nALL SITE MANAGEMENT TESTS PASSED")

if __name__ == "__main__":
    test_site_management()
