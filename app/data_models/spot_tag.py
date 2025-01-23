from typing import List

from pydantic import Field
from sqlmodel import Relationship, SQLModel

class SpotTag(SQLModel, table=True):
    spot_tag_id: int | None = Field(default=None, primary_key=True)
    spot_tag: str = Field(..., max_length=255)
