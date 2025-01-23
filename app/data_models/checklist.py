from typing import Optional
from pydantic import Field
from sqlmodel import Relationship

from travelPlaner_BackEnd.app.data_models.plan import Plan


class Checklist(SQLModel, table=True):
    plan_id: int = Field(primary_key=True, foreign_key="plan.plan_id")
    item: Optional[str] = Field(default=None, sa_column_kwargs={"length": 255})
    state: Optional[bool] = None

    plan: Plan = Relationship(back_populates="checklist")
