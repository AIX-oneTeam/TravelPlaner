from fastapi import APIRouter, HTTPException
from app.services.ai_agents.travel_agent_service import recommend_tourist_spots

router = APIRouter()  # APIRouter 객체 생성

@router.post("/recommendations")
async def get_recommendations(prompt: str):
    """
    관광지 추천 API
    Args:
        prompt (str): 사용자 입력 프롬프트
    Returns:
        dict: 추천 결과
    """
    try:
        recommendations = recommend_tourist_spots(prompt)
        return {"prompt": prompt, "recommendations": recommendations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
