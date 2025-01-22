import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from app.repository.db import Base

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

class Checklist(Base):
    __tablename__ = 'checklist'
    
    plan_id = Column(Integer, ForeignKey('plan.plan_id'), primary_key=True)
    item = Column(String(255), nullable=True)
    state = Column(Boolean, nullable=True)

    plan = relationship("Plan", back_populates="checklist")