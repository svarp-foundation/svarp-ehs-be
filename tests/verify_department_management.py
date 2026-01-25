
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
from app.models.company_db.department import Department
from app.models.company_db.finding import Finding
from app.models.company_db.audit import Audit

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

def test_department_management():
    db = next(get_db())
    cid = 301 # Distinct CID for this test
    
    # 1. Setup Admin
    email = "dep_admin@test.com"
    db.query(User).filter(User.email == email).delete()
    db.commit()
    admin = User(name="Dep Admin", email=email, password="pwd", role="admin", company_id=cid)
    db.add(admin)
    db.commit()
    
    token = create_access_token({"sub": email, "role": "admin", "company_id": cid, "user_id": admin.id})
    auth = {"Authorization": f"Bearer {token}"}
    
    # Ensure DB is migrated and clean
    cdb = get_company_app_db(cid)
    cdb.execute(text("DELETE FROM departments"))
    cdb.execute(text("DELETE FROM sites"))
    cdb.execute(text("DELETE FROM findings"))
    cdb.execute(text("DELETE FROM audits"))
    cdb.commit()
    
    print("\n[TEST] Starting Department Management Tests")

    # 2. Setup Site
    site = Site(name="Factory D", location="Test Loc")
    cdb.add(site)
    cdb.commit()
    site_id = site.id

    # 3. Test Create Department
    res = client.post("/department/create", json={"name": "Production", "site_id": site_id}, headers=auth)
    assert res.status_code == 200, f"Failed: {res.text}"
    dep_id = res.json()["id"]
    print("[SUCCESS] Created Department")

    # 4. Test Duplicate Name Constraint
    res = client.post("/department/create", json={"name": "Production", "site_id": site_id}, headers=auth)
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"]
    print("[SUCCESS] Prevented duplicate department name")

    # 5. Test Get Departments (verify has_findings=False)
    res = client.get("/department/all", headers=auth)
    assert res.status_code == 200
    deps = res.json()
    assert len(deps) == 1
    assert deps[0]["has_findings"] == False
    print("[SUCCESS] initial has_findings=False verified")

    # 6. Create Dependent Finding
    # First need an audit
    audit = Audit(title="Audit 1", audit_type="Int", site_id=site_id, status="In Progress")
    cdb.add(audit)
    cdb.commit()
    
    # Create finding linked by area name
    finding = Finding(audit_id=audit.id, area="Production", description="Found something")
    cdb.add(finding)
    cdb.commit()
    
    # 7. Test Get Departments (verify has_findings=True)
    res = client.get("/department/all", headers=auth)
    deps = res.json()
    assert deps[0]["has_findings"] == True
    print("[SUCCESS] has_findings=True verified after linking finding")

    # 8. Test Delete (Prevented)
    res = client.delete(f"/department/{dep_id}", headers=auth)
    assert res.status_code == 400
    assert "active findings" in res.json()["detail"]
    print("[SUCCESS] Blocked deletion when findings exist")

    # 9. Test Delete Finding -> Allow Department Delete
    cdb.query(Finding).delete()
    cdb.commit()
    
    res = client.delete(f"/department/{dep_id}", headers=auth)
    assert res.status_code == 200
    print("[SUCCESS] Deleted department after findings removed")

    # 10. Verify Delete
    res = client.get("/department/all", headers=auth)
    assert len(res.json()) == 0
    print("[SUCCESS] Validated department is gone")

    print("\nALL DEPARTMENT MANAGEMENT TESTS PASSED")

if __name__ == "__main__":
    test_department_management()
