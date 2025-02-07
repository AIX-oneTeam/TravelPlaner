from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
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
    prompt: Optional[str] = Field(default=None)

@router.post("/plan")
async def generate_plan(
    user_input: TravelPlanRequest,
    agent_type: List[str] = Query(..., alias="agent_type[]")
):
    """
    여행 일정을 생성하는 엔드포인트.
    - 입력은 JSON 본문으로 받고, 모든 필요한 필드를 포함합니다.
    - agent_type은 쿼리 파라미터로 전달됩니다.
    """
    try:
        print("프론트에서 받은 데이터:", user_input)
        input_dict = user_input.model_dump()
        # 쿼리 파라미터로 받은 agent_type을 입력 dict에 추가
        input_dict["agent_type"] = agent_type
        print("Python dict 변환:", input_dict)
        result = await create_plan(input_dict)
        return {
            "status": "success",
            "message": "일정과 장소 리스트가 생성되었습니다.",
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
