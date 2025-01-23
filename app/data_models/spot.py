from datetime import datetime
from typing import List, Optional

from pydantic import Field
from sqlmodel import Relationship, SQLModel

from app.data_models.plan_spot_map import PlanSpotMap
from app.data_models.plan_spot_tag_map import PlanSpotTagMap


class Spot(SQLModel, table=True):
    spot_id: Optional[int] = Field(default=None, primary_key=True)
    kor_name: str = Field(sa_column_kwargs={"length": 255})
    eng_name: Optional[str] = Field(default=None, sa_column_kwargs={"length": 255})
    description: str = Field(sa_column_kwargs={"length": 255})
    address: str = Field(sa_column_kwargs={"length": 255})
    zip: str = Field(sa_column_kwargs={"length": 10})
    url: Optional[str] = Field(default=None, sa_column_kwargs={"length": 2083})
    image_url: str = Field(sa_column_kwargs={"length": 2083})
    map_url: str = Field(sa_column_kwargs={"length": 2083})
    likes: Optional[int] = None
    satisfaction: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    spot_category: int
    phone_number: Optional[str] = Field(default=None, sa_column_kwargs={"length": 300})
    business_status: Optional[bool] = None
    business_hours: Optional[str] = Field(default=None, sa_column_kwargs={"length": 255})

    plan_spots: List["PlanSpotMap"] = Relationship(back_populates="spot")
    spot_tags: List["PlanSpotTagMap"] = Relationship(back_populates="spot")
