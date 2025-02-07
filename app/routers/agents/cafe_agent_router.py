from fastapi import APIRouter
from app.services.agents.cafe_agent_service import cafe_agent
from app.routers.agents.travel_all_schedule_agent_router import TravelPlanRequest
import asyncio
from datetime import datetime
router = APIRouter()

@router.post("/cafes")
async def get_cafes(user_input: TravelPlanRequest):
    """
    카페 정보를 가져오는 엔드포인트.
    - CrewAI 실행 후 일정(JSON) 반환.
    """
    start_time = datetime.now()   
    try:
        result = await asyncio.to_thread(
            cafe_agent, 
            user_input.model_dump()
        )
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        if not result:
            print("결과값이 없습니다")
        print(f"`cafe_agent()` 실행 시간: {execution_time:.4f}초")
        return {
            "status": "success",
            "message": "카페 리스트가 생성되었습니다.",
            "data": result.json_dict.get("spots",[]),
        }

    except asyncio.CancelledError:
        print("비동기 작업이 취소되었습니다.")
        raise  # 예외를 다시 발생
    
