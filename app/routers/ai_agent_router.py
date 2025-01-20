from fastapi import APIRouter
from api.ai_agents.travel_agent import router as travel_agent_router

router = APIRouter()

# 기존 라우터
# ...

# 여행 추천 라우터 추가
router.include_router(travel_agent_router, prefix="/ai/travel", tags=["AI Travel Agents"])
