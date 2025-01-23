from typing import Optional
from pydantic import Field
from sqlmodel import Relationship
from datetime import time

from travelPlaner_BackEnd.app.data_models.plan import Plan
from travelPlaner_BackEnd.app.data_models.spot import Spot


class PlanSpotMap(SQLModel, table=True):
    plan_id: int = Field(foreign_key="plan.plan_id", primary_key=True)
    spot_id: int = Field(foreign_key="spot.spot_id", primary_key=True)
    day_x: int = Field(...)
    order: int = Field(...)
    time: Optional[time] = Field(default=None)  # 시간 필드 추가

    plan: Plan = Relationship(back_populates="plan_spots")
    spot: Spot = Relationship(back_populates="plan_spots")
