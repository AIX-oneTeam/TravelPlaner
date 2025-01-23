from typing import Optional
from pydantic import Field
from sqlmodel import Relationship, SQLModel

from app.data_models.plan import Plan


class Checklist(SQLModel, table=True):
    plan_id: int = Field(primary_key=True, foreign_key=Plan.plan_id)
    item: str | None = Field(default=None, max_length=255)
    state: bool | None = Field(default=None)
