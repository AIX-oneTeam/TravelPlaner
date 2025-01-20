from sqlalchemy import Column, Integer, String
from app.services.mysql_service import Base

class Member(Base):
    __tablename__ = "member"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
