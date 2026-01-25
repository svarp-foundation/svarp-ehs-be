
import sys
import os
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from app.main import app
from app.db.master import SessionLocal
from app.models.user import User
from app.core.security import create_access_token
from app.db.company_session import get_company_db, migrate_company_db
from app.models.company_db.audit_team import AuditTeam
from app.models.company_db.audit_log import AuditLog
from app.db.db_session import get_company_engine
from sqlalchemy.orm import sessionmaker

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

def test_user_management_security():
    db = next(get_db())
    
    # 1. Setup Admin and Company
    admin_email = "admin_check@example.com"
    company_id = 999
    
    # Clean up
    db.query(User).filter(User.company_id == company_id).delete()
    db.commit()
    
    # Create Admin
    admin = User(name="Admin Check", email=admin_email, password="hashed", role="admin", company_id=company_id)
    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    token = create_access_token({"sub": admin_email, "role": "admin", "company_id": company_id, "user_id": admin.id})
    headers = {"Authorization": f"Bearer {token}"}
    
    # Setup Company DB
    cdb = get_company_app_db(company_id)
    cdb.query(AuditLog).delete() # Clear logs
    cdb.commit()
    
    print(f"\n[TEST] Created Admin ID: {admin.id}, Company: {company_id}")

    # 2. Test Create User
    res = client.post("/user/create", json={
        "name": "Auditor 1",
        "email": "auditor1@example.com",
        "password": "password",
        "role": "auditor"
    }, headers=headers)
    assert res.status_code == 200
    auditor_id = res.json()["user_id"]
    print("[SUCCESS] Admin created user")

    # Verify Audit Log
    log = cdb.query(AuditLog).filter(AuditLog.action == "CREATE", AuditLog.target_id == auditor_id).first()
    assert log is not None
    assert log.actor_id == admin.id
    print("[SUCCESS] User creation logged")

    # 3. Test Admin Change Own Role (Fail)
    res = client.put(f"/user/{admin.id}", json={"role": "auditor"}, headers=headers)
    assert res.status_code == 400
    assert "cannot change their own role" in res.json()["detail"]
    print("[SUCCESS] Admin prevented from changing own role")

    # 4. Test Admin Delete Self (Fail)
    res = client.delete(f"/user/{admin.id}", headers=headers)
    assert res.status_code == 400
    assert "cannot delete your own account" in res.json()["detail"]
    print("[SUCCESS] Admin prevented from deleting self")

    # 5. Test Delete User Assigned to Audit (Fail)
    # create audit team assignment
    team = AuditTeam(audit_id=1, auditor_id=auditor_id)
    cdb.add(team)
    cdb.commit()
    
    res = client.delete(f"/user/{auditor_id}", headers=headers)
    assert res.status_code == 400
    assert "assigned to audits" in res.json()["detail"]
    print("[SUCCESS] Blocked deleting user assigned to audit")
    
    # Cleanup Assignment
    cdb.delete(team)
    cdb.commit()

    # 6. Test Successful Delete + Log
    res = client.delete(f"/user/{auditor_id}", headers=headers)
    assert res.status_code == 200
    print("[SUCCESS] Deleted user after clearing assignments")
    
    log = cdb.query(AuditLog).filter(AuditLog.action == "DELETE", AuditLog.target_id == auditor_id).first()
    assert log is not None
    print("[SUCCESS] User deletion logged")

    cdb.close()
    
    print("\nALL SECURITY TESTS PASSED")

if __name__ == "__main__":
    test_user_management_security()
