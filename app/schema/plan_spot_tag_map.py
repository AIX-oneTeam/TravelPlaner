"""__summary__ : 장소와 태그 매핑 스키마입니다."""
from pydantic import BaseModel, Field

class PlanSpotTagMap(BaseModel):
    spot_id: int = Field(..., description="Spot ID")
    spot_tag_id: int = Field(..., description="Spot Tag ID")
