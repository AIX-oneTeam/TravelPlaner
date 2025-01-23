from datetime import datetime
from pydantic import Field
from sqlmodel import SQLModel

class Test(SQLModel, table=True):
    spot_id: int | None = Field(default=None, primary_key=True)
    kor_name: str = Field(..., max_length=255)
    eng_name: str | None = Field(default=None, max_length=255)
    description: str = Field(..., max_length=255)
    address: str = Field(..., max_length=255)
    zip: str = Field(..., max_length=10)
    url: str | None = Field(default=None, max_length=2083)
    image_url: str = Field(default=None, max_length=2083)
    map_url: str = Field(default=None, max_length=2083)
    likes: int | None = Field(default=None)
    satisfaction: float | None = Field(default=None)
    created_at: datetime | None = Field(default_factory=datetime.utcnow)  # 기본값 지정
    updated_at: datetime | None = Field(default_factory=datetime.utcnow)
    spot_category: int = Field(...)
    phone_number: str | None = Field(default=None, max_length=300)
    business_status: bool | None = None
    business_hours: str | None = Field(default=None, max_length=255)

