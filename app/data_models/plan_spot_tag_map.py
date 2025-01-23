from pydantic import Field
from sqlmodel import Relationship, SQLModel

from app.data_models.spot import Spot
from app.data_models.spot_tag import SpotTag


class PlanSpotTagMap(SQLModel, table=True):
    spot_id: int = Field(foreign_key="spot.spot_id", primary_key=True)
    spot_tag_id: int = Field(foreign_key="spot_tag.spot_tag_id", primary_key=True)

    spot: Spot = Relationship(back_populates="spot_tags")
    spot_tag: SpotTag = Relationship(back_populates="spot_tags")
