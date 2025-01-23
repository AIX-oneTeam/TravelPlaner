

from datetime import datetime
from typing import List

from pydantic import Field
from sqlmodel import Relationship, SQLModel

from app.data_models.checklist import Checklist
from app.data_models.member import Member
from app.data_models.plan_spot_map import PlanSpotMap


class Plan(SQLModel, table=True):
    plan_id: int | None = Field(default=None, primary_key=True)
    plan_name: str | None = Field(default=None, max_length=255)
    start_date: datetime | None = Field(default=None)
    end_date: datetime | None = Field(default=None)
    main_location: str | None = Field(default=None, max_length=50)
    ages: int | None = Field(default=None)
    companion_count: int | None = Field(default=None)
    plan_concepts: str | None = Field(default=None, max_length=255)
    member_id: int = Field(foreign_key="member.member_id")

    member: Member = Relationship(back_populates="plans")
    checklist: Checklist | None = Relationship(back_populates="plan")
    plan_spots: List["PlanSpotMap"] = Relationship(back_populates="plan")
