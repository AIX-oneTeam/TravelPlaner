"""__summary__ : 여행 계획 스키마입니다. 식별자는 id입니다."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class Plan(BaseModel):
    plan_id: Optional[int] = Field(None, description="Plan ID")
    plan_name: Optional[str] = Field(None, max_length=255, description="Plan name")
    start_date: Optional[datetime] = Field(None, description="Start date")
    end_date: Optional[datetime] = Field(None, description="End date")
    main_location: Optional[str] = Field(None, max_length=50, description="Main location")
    ages: Optional[int] = Field(None, description="Ages of participants")
    companion_count: Optional[int] = Field(None, description="Number of companions")
    plan_concepts: Optional[str] = Field(None, max_length=255, description="Plan concepts")
    member_id: int = Field(..., description="Member ID")
