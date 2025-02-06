from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.services.agents.travel_all_schedule_agent_service import create_plan

router = APIRouter()

class Companion(BaseModel):
    label: str
    count: int

class TravelPlanRequest(BaseModel):
    ages: str
    companion_count: List[Companion]
    start_date: str
    end_date: str
    concepts: List[str]
    main_location: str
    agent_type: List[str]  # 추가된 필드

@router.post("/plan")
async def generate_plan(user_input: TravelPlanRequest):
    """
    여행 일정을 생성하는 엔드포인트.
    - 입력은 JSON 본문으로 받고, 모든 필요한 필드를 포함합니다.
    """
    try:
        print("프론트에서 받은 데이터:", user_input)
        print("Python dict 변환:", user_input.model_dump())
        result = await create_plan(user_input.model_dump())
        return {
            "status": "success",
            "message": "일정과 장소 리스트가 생성되었습니다.",
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
