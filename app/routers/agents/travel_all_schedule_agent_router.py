# app/routers/agents/travel_all_schedule_agent_router.py
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from app.services.agents.travel_all_schedule_agent_service import create_plan
from app.services.agents.site_agent_service import TravelPlanAgentService
from app.services.agents.restaurant_agent_service import create_recommendation
from app.services.agents.accommodation_agent_4 import run
from app.services.agents.cafe_agent_service import CafeAgentService

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
    try:
        print("프론트에서 받은 데이터:", user_input)

        # Pydantic 모델을 Python dict로 변환 후, 에이전트 타입 추가
        input_dict = user_input.model_dump()
        input_dict["agent_type"] = agent_type

        # 각 외부 에이전트 호출 및 결과 집계
        external_data = {}
        if "restaurant" in agent_type:
            # 맛집 에이전트 호출 (동기 또는 비동기 여부에 따라 처리)
            external_data["restaurant"] = create_recommendation(input_dict)
        if "site" in agent_type:
            site_agent_service = TravelPlanAgentService()
            external_data["site"] = await site_agent_service.create_tourist_plan(
                input_dict
            )
        if "cafe" in agent_type:
            cafe_agent_service = CafeAgentService()
            external_data["cafe"] = await cafe_agent_service.cafe_agent(input_dict)
        if "accommodation" in agent_type:
            external_data["accommodation"] = run(input_dict)

        # 집계한 외부 데이터를 입력 데이터에 추가합니다.
        input_dict["external_data"] = external_data
        print("집계된 external_data:", external_data)

        # 최종 여행 일정 생성 함수 호출 (외부 데이터가 포함된 상태)
        result = await create_plan(input_dict)

        return {
            "status": "success",
            "message": "일정과 장소 리스트가 생성되었습니다.",
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
