from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.services.agents.travel_all_schedule_agent_service import create_plan

router = APIRouter()

# Pydantic 모델 정의
class Companion(BaseModel):
    label: str
    count: int


class TravelPlanRequest(BaseModel):
    ageGroup: str
    companions: List[
        Companion
    ]
    start_date: str
    end_date: str
    concepts: List[str]
    location: str

@router.post("/plan")
async def generate_plan(user_input: TravelPlanRequest):
    """
    여행 일정을 생성하는 엔드포인트.
    - CrewAI 실행 후 일정(JSON) 반환.
    """
    try:
        print("프론트에서 받은 데이터:", user_input)  # 요청 데이터 출력
        print("Python dict 변환:", user_input.model_dump())  # dict로 변환 후 출력
        result = await create_plan(user_input.model_dump())
        return {
            "status": "success",
            "message": "일정과 장소 리스트가 생성되었습니다.",
            "data": result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
