import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from app.repository.db import Base

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship

class Spot(Base):
    __tablename__ = 'spot'
    
    spot_id = Column(Integer, primary_key=True, autoincrement=True)
    kor_name = Column(String(255), nullable=False)
    eng_name = Column(String(255), nullable=True)
    description = Column(String(255), nullable=False)
    address = Column(String(255), nullable=False)
    zip = Column(CHAR(10), nullable=False)
    url = Column(String(2083), nullable=True)
    image_url = Column(String(2083), nullable=False)
    map_url = Column(String(2083), nullable=False)
    likes = Column(Integer, nullable=True)
    satisfaction = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    spot_category = Column(Integer, nullable=False)
    phone_number = Column(String(300), nullable=True)
    business_status = Column(Boolean, nullable=True)
    business_hours = Column(String(255), nullable=True)