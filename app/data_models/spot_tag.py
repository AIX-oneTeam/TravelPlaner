import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from app.repository.db import Base

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

class SpotTag(Base):
    __tablename__ = "spot_tag"
    spot_tag_id = Column(Integer, primary_key=True, autoincrement=True)
    spot_tag = Column(String(255), nullable=False)
    spot_tag_maps = relationship("PlanSpotTagMap", back_populates="spot_tag")

