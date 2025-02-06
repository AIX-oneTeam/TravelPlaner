from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from app.services.agents.restaurant_agent_service import (
    create_recommendation,
)  # ✅ 올바른 함수 임포트

router = APIRouter()


# Pydantic 모델 정의 (prompt 포함)
class Companion(BaseModel):
    label: str
    count: int


class TravelPlanRequest(BaseModel):
    main_location: str
    start_date: str
    end_date: str
    ages: str
    companions: List[Companion]
    concepts: List[str]
    prompt: Optional[str] = Field(default=None)


@router.post("/restaurant")
async def generate_plan(user_input: TravelPlanRequest):
    """
    맛집 추천 엔드포인트
    """
    try:
        print("프론트에서 받은 데이터:", user_input)

        print("Python dict 변환:", user_input.model_dump())
        result = create_recommendation(user_input.model_dump())
        print("restaurant_response:", result)

        return {
            "status": "success",
            "message": "맛집 리스트가 생성되었습니다.",
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
