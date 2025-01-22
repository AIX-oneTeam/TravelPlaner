import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from app.repository.db import Base

from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

class PlanSpotTagMap(Base):
    __tablename__ = 'plan_spot_tag_map'
    
    spot_id = Column(Integer, ForeignKey('spot.spot_id'), primary_key=True)
    spot_tag_id = Column(Integer, ForeignKey('spot_tag.spot_tag_id'), primary_key=True)
