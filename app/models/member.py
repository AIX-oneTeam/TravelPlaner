from sqlalchemy import Column, Integer, String
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from sqlalchemy import Column, Integer, String, Date, DateTime
from app.db import Base
class Member(Base):
    __tablename__ = "member"
    id = Column(Integer, nullable=False, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    email = Column(String(255), nullable=False)
    access_token = Column(String(255), nullable=True) # false로 바꾸기
    refresh_token = Column(String(255), nullable=True) # false로 바꾸기
    oauth = Column(String(255), nullable=True) # false로 바꾸기
    nickname = Column(String(50), nullable=True)
    sex = Column(String(10), nullable=True)
    picture_url = Column(String(2083), nullable=True)
    birth = Column(Date, nullable=True)
    address = Column(String(255), nullable=True)
    zip = Column(String(10), nullable=True)
    phone_umber = Column(String(20), nullable=True)
    voice = Column(String(255), nullable=True)
    role = Column(String(10), nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

# # # 테이블 생성
# Base.metadata.create_all(bind=engine)

# print("테이블 생성 완료!")