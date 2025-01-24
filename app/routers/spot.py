from fastapi import APIRouter

from app.schema.plan import Plan
from app.services.plans.plan_service import reg_plan


router = APIRouter()

# 일정 저장
@router.post("/spots")
async def create_plan(plan: Plan, member_id: int):
    reg_plan(plan, member_id)
    
    
