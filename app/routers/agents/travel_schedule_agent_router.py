from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.services.agents.travel_all_schedule_agent_service import create_plan

router = APIRouter()


# ✅ Pydantic 모델 정의
class Companion(BaseModel):
    label: str  # 예: "성인", "반려견"
    count: int  # 예: 2, 1


class TravelPlanRequest(BaseModel):
    ageGroup: str  # 예: "20대"
    companions: List[
        Companion
    ]  # [{label: '성인', count: 2}, {label: '반려견', count: 1}]
    start_date: str  # 예: "2025-01-31 00:00:00"
    end_date: str  # 예: "2025-02-02 00:00:00"
    concepts: List[str]  # ["맛집", "바다"]
    location: str  # "부산광역시"


@router.post("/plan")
async def generate_plan(user_input: TravelPlanRequest):
    """
    여행 일정을 생성하는 엔드포인트.
    - CrewAI 실행 후 일정(JSON) 반환.
    """
    try:
        print("프론트에서 받은 데이터:", user_input)  # ✅ 요청 데이터 출력
        print("Python dict 변환:", user_input.model_dump())  # ✅ dict로 변환 후 출력
        result = await create_plan(user_input.model_dump())  # ✅ `model_dump()` 사용
        return {
            "status": "success",
            "message": "일정과 장소 리스트가 생성되었습니다.",
            "data": result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))  # 🔹 예외 발생 시 처리
