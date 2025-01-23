from datetime import datetime
from typing import List, Optional

from pydantic import Field
from sqlmodel import Relationship, SQLModel

from app.data_models.plan_spot_map import PlanSpotMap
from app.data_models.plan_spot_tag_map import PlanSpotTagMap


class Spot(SQLModel, table=True):
    spot_id: int | None = Field(default=None, primary_key=True)
    kor_name: str = Field(..., max_length=255)
    eng_name: str | None = Field(default=None, max_length=255)
    description: str = Field(..., max_length=255)
    address: str = Field(..., max_length=255)
    zip: str = Field(..., max_length=10)
    url: str | None = Field(default=None, max_length=2083)
    image_url: str = Field(default=None, max_length=2083)
    map_url: str = Field(default=None, max_length=2083)
    likes: int | None = Field(default=None)
    satisfaction: float | None = Field(default=None)
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)
    spot_category: int = Field(...)
    phone_number: str | None = Field(default=None, default=None, max_length=300)
    business_status: bool | None = None
    business_hours: str | None = Field(default=None, max_length=255)

    plan_spots: List["PlanSpotMap"] = Relationship(back_populates="spot")
    spot_tags: List["PlanSpotTagMap"] = Relationship(back_populates="spot")
