# routers/travel_plan_router.py

from fastapi import APIRouter
from pydantic import BaseModel
from services.travel_agent_service import create_travel_plan

router = APIRouter()

# (필수 아님) 요청 바디를 위해 Pydantic 모델 정의
class TravelPlanRequest(BaseModel):
    location: str
    date: str
    age_group: str
    companions: str

@router.post("/travel-plan")
def get_travel_plan(request: TravelPlanRequest):
    """
    요청 예:
    {
      "location": "제주도",
      "date": "2025/01/20",
      "age_group": "성인",
      "companions": "성인2명, 청소년1명"
    }
    """
    results = create_travel_plan(
        location=request.location,
        date=request.date,
        age_group=request.age_group,
        companions=request.companions
    )
    # 예: {
    #   "food_cafe": [
    #       {"picture_url": "...", "name": "...", "description": "..."},
    #       ... 총 5개
    #   ],
    #   "attraction": [... 5개],
    #   "accommodation": [... 5개]
    # }
    return results
