from fastapi import APIRouter, HTTPException
from app.services.plan_all_service import create_plan
from pydantic import BaseModel
from typing import List, Dict

router = APIRouter()

# 요청 본문 스키마 정의
class UserInput(BaseModel):
    location: str
    start_date: str
    end_date: str
    ages: int
    companions: Dict[str, int]
    concepts: List[str]

@router.post("/generate")
def generate_test_plan(user_input: UserInput):
    """
    테스트용으로 여행 일정을 생성하는 엔드포인트.
    - 정해진 입력값을 사용하여 일정(JSON) 반환.
    """
    try:
        # ✅ 서비스 호출
        result = create_plan(user_input.dict())

        # ✅ 결과 반환
        return {
            "status": "success",
            "message": "테스트 일정과 장소 리스트가 생성되었습니다.",
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")
