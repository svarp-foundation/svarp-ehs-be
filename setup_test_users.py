from app.db.master import SessionLocal
from app.models.user import User
from app.core.security import hash_password

def setup_users():
    db = SessionLocal()
    try:
        # Define users to create
        users = [
            {"email": "admin_c1@example.com", "password": "password123", "role": "admin", "company_id": 1, "name": "Admin C1"},
            {"email": "auditor_c1@example.com", "password": "password123", "role": "auditor", "company_id": 1, "name": "Auditor C1"},
            {"email": "admin_c2@example.com", "password": "password123", "role": "admin", "company_id": 2, "name": "Admin C2"},
        ]

        for u_data in users:
            user = db.query(User).filter(User.email == u_data["email"]).first()
            if not user:
                print(f"Creating user {u_data['email']}...")
                user = User(
                    email=u_data["email"],
                    password=hash_password(u_data["password"]),
                    role=u_data["role"],
                    company_id=u_data["company_id"],
                    name=u_data["name"]
                )
                db.add(user)
            else:
                # Update password to ensure we know it
                user.password = hash_password(u_data["password"])
                print(f"Updated password for {u_data['email']}")
        
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    setup_users()
