from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class spot_pydantic(BaseModel):
    kor_name: str = Field(max_length=255)
    eng_name: Optional[str] = Field(default=None, max_length=255)
    address: str = Field(max_length=255)

    url: Optional[str] = Field(default=None, max_length=2083)
    image_url: str = Field(max_length=2083)
    map_url: str = Field(max_length=2083)

    spot_category: int
    phone_number: Optional[str] = Field(default=None, max_length=300)  # Optional로 변경
    business_status: Optional[bool] = None
    business_hours: Optional[str] = Field(default=None, max_length=255)
    order: int
    day_x: int
    spot_time: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class spots_pydantic(BaseModel):
    spots: list[spot_pydantic]


def calculate_trip_days(start_date_str: str, end_date_str: str) -> int:
    fmt = "%Y-%m-%d"
    start_dt = datetime.strptime(start_date_str, fmt)
    end_dt = datetime.strptime(end_date_str, fmt)
    delta = end_dt - start_dt
    return delta.days + 1
