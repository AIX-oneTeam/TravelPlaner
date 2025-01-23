from pydantic import Field
from sqlmodel import Relationship, SQLModel

from app.data_models.spot import Spot
from app.data_models.spot_tag import SpotTag


class PlanSpotTagMap(SQLModel, table=True):
    spot_id: int = Field(foreign_key=Spot.spot_id, primary_key=True)
    spot_tag_id: int = Field(foreign_key=SpotTag.spot_tag_id, primary_key=True)

