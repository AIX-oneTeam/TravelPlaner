"""__summary__ : 장소 스키마입니다. 식별자는 id입니다."""
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from typing import Optional

class Spot(BaseModel):
    spot_id: Optional[int] = Field(None, description="Spot ID")
    kor_name: str = Field(..., max_length=255, description="Korean name")
    eng_name: Optional[str] = Field(None, max_length=255, description="English name")
    description: str = Field(..., max_length=255, description="Description")
    address: str = Field(..., max_length=255, description="Address")
    zip: str = Field(..., max_length=10, description="Zip code")
    url: Optional[HttpUrl] = Field(None, description="URL")
    image_url: HttpUrl = Field(..., description="Image URL")
    map_url: HttpUrl = Field(..., description="Map URL")
    likes: Optional[int] = Field(None, description="Number of likes")
    satisfaction: Optional[float] = Field(None, description="Satisfaction score")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")
    spot_category: int = Field(..., description="Spot category")
    phone_number: Optional[str] = Field(None, max_length=300, description="Phone number")
    business_status: Optional[bool] = Field(None, description="Business status")
    business_hours: Optional[str] = Field(None, max_length=255, description="Business hours")
