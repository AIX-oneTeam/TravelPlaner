"""__summary__ : 장소 태그 스키마입니다. 식별자는 id입니다."""
from pydantic import BaseModel, Field
from typing import Optional

class SpotTag(BaseModel):
    spot_tag_id: Optional[int] = Field(None, description="Spot Tag ID")
    spot_tag: str = Field(..., max_length=255, description="Spot tag")
