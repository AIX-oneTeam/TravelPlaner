import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from app.repository.db import Base


from sqlalchemy import Column, Integer, ForeignKey

class PlanSpotMap(Base):
    __tablename__ = 'plan_spot_map'
    
    plan_id = Column(Integer, ForeignKey('plan.plan_id'), primary_key=True)
    spot_id = Column(Integer, ForeignKey('spot.spot_id'), primary_key=True)
    day_x = Column(Integer, nullable=False)
    order = Column(Integer, nullable=False)