from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from typing import List, Optional
from app.services.agents.restaurant_agent_service import create_recommendation
from app.routers.agents.travel_all_schedule_agent_router import TravelPlanRequest

router = APIRouter()


# Pydantic 모델 정의 (prompt 포함)
class Companion(BaseModel):
    label: str
    count: int


@router.post("/restaurant")
async def get_restaurants(
    user_input: TravelPlanRequest = Body(...),
    prompt: Optional[str] = Query(None),
):
    """
    맛집 추천 엔드포인트
    """
    try:
        # model_dump()를 사용하여 입력 데이터를 dict 형태로 변환
        user_data = user_input.model_dump()

        # prompt 값이 있을 경우, 딕셔너리에 추가 (user_input에는 직접 할당 불가)
        if prompt:
            user_data["prompt"] = prompt

        print("프론트에서 받은 데이터:", user_data)

        # create_recommendation 호출 시 await 사용 (비동기 함수이므로)
        try:
            result = await create_recommendation(user_data, prompt)
        except Exception as e:
            print(f"[ERROR] create_recommendation() 오류 발생: {e}")
            raise HTTPException(status_code=500, detail="추천 생성 중 오류 발생")

        print("restaurant_response:", result)

        return {
            "status": "success",
            "message": "맛집 리스트가 생성되었습니다.",
            "data": result,
        }

    except Exception as e:
        print(f"[ERROR] 요청 처리 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=str(e))
