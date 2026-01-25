
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

def test_finding_management():
    db = next(get_db())
    cid = 303 # Distinct CID
    
    # 1. Setup Admin & Auditor
    email_admin = "finding_admin@test.com"
    email_auditor = "finding_auditor@test.com"
    
    db.query(User).filter(User.email.in_([email_admin, email_auditor])).delete()
    db.commit()
    
    admin = User(name="F Admin", email=email_admin, password="pwd", role="admin", company_id=cid)
    auditor = User(name="F Auditor", email=email_auditor, password="pwd", role="auditor", company_id=cid)
    db.add(admin)
    db.add(auditor)
    db.commit()
    
    token = create_access_token({"sub": email_admin, "role": "admin", "company_id": cid, "user_id": admin.id})
    auth = {"Authorization": f"Bearer {token}"}
    
    # Clean DB
    cdb = get_company_app_db(cid)
    cdb.execute(text("DELETE FROM findings"))
    cdb.execute(text("DELETE FROM audits"))
    cdb.execute(text("DELETE FROM sites"))
    cdb.commit()
    
    print("\n[TEST] Starting Finding Management Tests")

    # 2. Setup Site & Audit
    site = Site(name="Factory F", location="Finding City")
    cdb.add(site)
    cdb.commit()
    
    audit = Audit(title="Audit F", audit_type="Int", site_id=site.id, status="in_progress")
    cdb.add(audit)
    cdb.commit()
    audit_id = audit.id

    # 3. Create Finding (Open by default)
    res = client.post("/finding/create", json={
        "audit_id": audit_id,
        "category": "Safety",
        "type": "NC",
        "description": "Loose wire",
        "likelihood": 2,
        "severity": 2
    }, headers=auth)
    assert res.status_code == 201
    finding_id = res.json()["id"]
    print("[SUCCESS] Created Finding")
    
    # Verify default state
    f = cdb.query(Finding).filter(Finding.id == finding_id).first()
    assert f.status == "open"
    assert f.assigned_to_id is None
    print("[SUCCESS] Default status is 'open', unassigned")

    # 4. Update: key status + Assign
    res = client.patch(f"/finding/{finding_id}", json={
        "status": "in_progress",
        "assigned_to_id": auditor.id
    }, headers=auth)
    assert res.status_code == 200
    print("[SUCCESS] Updated status and assignee")
    
    # Verify DB
    db.expire_all()
    # Need to re-fetch from company DB, handle session cleanly
    cdb.expire_all()
    f = cdb.query(Finding).filter(Finding.id == finding_id).first()
    assert f.status == "in_progress"
    assert f.assigned_to_id == auditor.id
    print("[SUCCESS] Verified update in DB")

    # 5. Invalid Assignment (User from another company)
    # Create alien user
    email_alien = "alien@other.com"
    db.query(User).filter(User.email == email_alien).delete()
    alien = User(name="Alien", email=email_alien, password="pwd", role="auditor", company_id=999)
    db.add(alien)
    db.commit()
    
    res = client.patch(f"/finding/{finding_id}", json={
        "assigned_to_id": alien.id
    }, headers=auth)
    assert res.status_code == 400
    assert "same company" in res.json()["detail"]
    print("[SUCCESS] Blocked assignment to external user")

    # 6. List Findings (Check assigned_name)
    res = client.get("/finding/get-all", headers=auth)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["assigned_name"] == "F Auditor"
    assert data[0]["status"] == "in_progress"
    print("[SUCCESS] List returns status and assignee name")

    print("\nALL FINDING MANAGEMENT TESTS PASSED")

if __name__ == "__main__":
    test_finding_management()
