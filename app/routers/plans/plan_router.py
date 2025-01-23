
from fastapi import APIRouter, Response

from app.data_models.plan import Plan
from app.dtos.common.response import ErrorResponse, SuccessResponse
from app.services.plans.plans_service import reg_plan


router = APIRouter()

# 일정 저장
@router.post("/plans")
async def create_plan(plan: Plan, member_id: int):

    try:
        plan_id = await reg_plan(plan, member_id)
        return SuccessResponse(data={"plan_id": plan_id}, message="일정이 성공적으로 등록되었습니다.")
    except Exception as e:
        return ErrorResponse(message="일정 등록에 실패했습니다.", error_detail=e)