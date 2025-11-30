from sqlalchemy import Column, Integer, String
from app.db.base_class import Base

class Site(Base):
    __tablename__ = "sites"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    location = Column(String, nullable=True)
