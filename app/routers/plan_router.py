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
        result = create_plan(user_input)  # ✅ CrewAI 실행 후 결과 받기

        # ✅ 실행 결과 검증
        if not isinstance(result, dict) or "plan" not in result or "spots" not in result:
            raise ValueError("CrewAI 실행 결과가 올바른 JSON 형식이 아닙니다.")

        # ✅ 라우터에서 `response_json` 조립
        response_json = {
            "status": "success",
            "message": "일정과 장소 리스트가 생성되었습니다.",
            "plan": result["plan"],
            
            "spots": result["spots"]
        }

        return response_json  # ✅ 최종 JSON 응답 반환
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")  # 🔹 예외 발생 시 처리
