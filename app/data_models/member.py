import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from app.repository.db import Base

from sqlalchemy import Column, Integer, String, Date, DateTime
from sqlalchemy.orm import relationship

class Member(Base):
    __tablename__ = 'member'
    
    member_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    email = Column(String(255), nullable=False)
    access_token = Column(String(255), nullable=False)
    refresh_token = Column(String(255), nullable=False)
    oauth = Column(String(255), nullable=False)
    nickname = Column(String(50), nullable=True)
    sex = Column(String(10), nullable=True)
    picture_url = Column(String(2083), nullable=True)
    birth = Column(String, nullable=True)
    address = Column(String(255), nullable=True)
    zip = Column(String(10), nullable=True)
    phone_number = Column(String(20), nullable=True)
    voice = Column(String(255), nullable=True)
    role = Column(String(10), nullable=True)

    plans = relationship("Plan", back_populates="member")
# # # 테이블 생성
# Base.metadata.create_all(bind=engine)

# print("테이블 생성 완료!")
