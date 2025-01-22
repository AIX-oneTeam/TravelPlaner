"""__summary__ : 체크리스트 스키마입니다. 식별자는 plan_id입니다."""
from pydantic import BaseModel, Field
from typing import Optional

class Checklist(BaseModel):
    plan_id: int = Field(..., description="Plan ID")
    item: Optional[str] = Field(None, max_length=255, description="Checklist item")
    state: Optional[bool] = Field(None, description="State of the checklist item")
