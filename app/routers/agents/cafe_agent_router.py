from fastapi import APIRouter, HTTPException
from app.services.agents.cafe_agent_service import cafe_agent
from app.routers.agents.travel_all_schedule_agent_router import TravelPlanRequest

router = APIRouter()

@router.post("/cafe")
async def cafe_response_test(user_input: TravelPlanRequest):
    """
    카페 정보를 가져오는 엔드포인트.
    - CrewAI 실행 후 일정(JSON) 반환.
    """
    try:
        result = cafe_agent(user_input.model_dump())
        return {
            "status": "success",
            "message": "카페 리스트가 생성되었습니다.",
            "data": result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))