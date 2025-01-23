from typing import List, Optional

from pydantic import Field
from sqlmodel import Relationship


class SpotTag(SQLModel, table=True):
    spot_tag_id: Optional[int] = Field(default=None, primary_key=True)
    spot_tag: str = Field(sa_column_kwargs={"length": 255})

    spot_tags: List["PlanSpotTagMap"] = Relationship(back_populates="spot_tag")
