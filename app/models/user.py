from sqlalchemy import Column, Integer, String
from app.db.base_class import Base

class User(Base):
    __tablename__ = "master_users"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password = Column(String)  # hashed
    role = Column(String)      # admin / auditor / etc
