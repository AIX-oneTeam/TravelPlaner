"""__summary__ : 여행 계획과 장소 매핑 스키마입니다."""
from pydantic import BaseModel, Field

class PlanSpotMap(BaseModel):
    plan_id: int = Field(..., description="Plan ID")
    spot_id: int = Field(..., description="Spot ID")
    day_X: int = Field(..., description="Day number in the plan")
    order: int = Field(..., description="Order of the spot in the plan")
