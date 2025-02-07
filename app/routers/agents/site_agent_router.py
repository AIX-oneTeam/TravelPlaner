from fastapi import APIRouter, HTTPException
from app.services.agents.site_agent import create_tourist_plan, TravelPlanRequest
import asyncio

router = APIRouter()


@router.post("/plan")
async def get_site_plan(user_input: TravelPlanRequest):
    """
    site_agent를 이용한 관광지(또는 여행지) 추천 엔드포인트.
    클라이언트는 main_location, start_date, end_date, ages, companion_count, concepts 등의 정보를 JSON 형식으로 전송합니다.
    """
    try:
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, create_tourist_plan, user_input.dict()
        )
        return {
            "status": "success",
            "message": "관광지 추천 결과가 생성되었습니다.",
            "data": result.dict(),  # Pydantic 모델을 dict로 변환하여 반환
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
