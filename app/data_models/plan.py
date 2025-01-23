from datetime import datetime
from typing import List, Optional

from pydantic import Field
from sqlmodel import Relationship, SQLModel

from app.data_models.checklist import Checklist
from app.data_models.member import Member
from app.data_models.plan_spot_map import PlanSpotMap

class Plan(SQLModel, table=True):
    plan_id: Optional[int] = Field(default=None, primary_key=True)
    plan_name: Optional[str] = Field(default=None, sa_column_kwargs={"length": 255})
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    main_location: Optional[str] = Field(default=None, sa_column_kwargs={"length": 50})
    ages: Optional[int] = None
    companion_count: Optional[int] = None
    plan_concepts: Optional[str] = Field(default=None, sa_column_kwargs={"length": 255})
    member_id: int = Field(foreign_key="member.member_id")

    member: Member = Relationship(back_populates="plans")
    checklist: Optional["Checklist"] = Relationship(back_populates="plan")
    plan_spots: List["PlanSpotMap"] = Relationship(back_populates="plan")
