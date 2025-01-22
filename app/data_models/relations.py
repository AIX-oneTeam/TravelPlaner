import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from app.repository.db import Base

from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

class PlanSpotMap(Base):
    __tablename__ = "plan_spot_map"
    plan_id = Column(Integer, ForeignKey("plan.plan_id"), primary_key=True)
    spot_id = Column(Integer, ForeignKey("spot.spot_id"), primary_key=True)
    plan = relationship("Plan", back_populates="spots")
    spot = relationship("Spot", back_populates="plan_spots")

class PlanSpotTagMap(Base):
    __tablename__ = "plan_spot_tag_map"
    spot_id = Column(Integer, ForeignKey("spot.spot_id"), primary_key=True)
    spot_tag_id = Column(Integer, ForeignKey("spot_tag.spot_tag_id"), primary_key=True)
    spot_tag = relationship("SpotTag", back_populates="spot_tag_maps")