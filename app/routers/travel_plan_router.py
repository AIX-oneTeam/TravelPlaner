# app/routers/travel_plan_router.py
from fastapi import APIRouter
from app.services.agents.travel_agent_service import c

router = APIRouter()

@router.post("/travel-plan")
async def generate_travel_plan(request: TravelPlanRequest):
    result = await create_travel_plan(
        location="제주도",
        start_date=request.start_date,
        end_date=request.end_date,
        age=request.age,
        companions=request.companions
    )
    return result
