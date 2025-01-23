
from fastapi import APIRouter


router = APIRouter()

# 일정 저장
@router.post("/plans_spots")
async def create_plan_spot():
    pass
