from fastapi import APIRouter, HTTPException
from typing import Dict
from app.services.plan_all_service import create_plan

router = APIRouter()

@router.post("/")
def generate_plan(user_input: Dict):
    """
    여행 일정을 생성하는 엔드포인트.
    - CrewAI 실행 후 일정(JSON) 반환.
    """

    try:
        result = create_plan(user_input)  # ✅ `await` 없이 호출
        return {"status": "success", "message": "일정과 장소 리스트가 생성되었습니다.", "data": result}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))  # 🔹 예외 발생 시 처리
