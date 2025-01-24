
from fastapi import APIRouter, Request

from app.data_models.data_model import Plan
from app.dtos.common.response import ErrorResponse, SuccessResponse
from app.services.plans.plan_service import reg_plan


router = APIRouter()

# 일정 저장
@router.post("/")
def create_plan(plan: Plan, member_id: int, request: Request):

    try:
        plan_id = reg_plan(plan, member_id, request)
        return SuccessResponse(data={"plan_id": plan_id}, message="일정이 성공적으로 등록되었습니다.")
    except Exception as e:
        return ErrorResponse(message="일정 등록에 실패했습니다.", error_detail=e)