import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from app.repository.db import Base

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship

class Plan(Base):
    __tablename__ = "plan"
    plan_id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey("member.member_id"), nullable=False)
    plan_name = Column(String(255), nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    main_location = Column(String(50), nullable=True)
    ages = Column(Integer, nullable=True)
    companion_count = Column(Integer, nullable=True)
    plan_concepts = Column(Integer, nullable=True)
    member = relationship("Member", back_populates="plans")
    checklist = relationship("Checklist", uselist=False, back_populates="plan")
    spots = relationship("PlanSpotMap", back_populates="plan")
