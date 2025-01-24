
from fastapi import APIRouter, Request

from app.dtos.common.response import ErrorResponse, SuccessResponse
from app.services.plans.plan_spots_service import find_plan_spots


router = APIRouter()

# 일정 저장
@router.post("/")
async def create_plan_spot():
    pass

@router.get("/{plan_id}")
async def read_plan_spots(plan_id: int, request: Request):
    try:
        plan_spots = find_plan_spots(plan_id, request)
        return SuccessResponse(data={"plan_spots": plan_spots}, message="일정 장소가 성공적으로 조회되었습니다.")
    except Exception as e:
        return ErrorResponse(message="일정 장소 조회에 실패했습니다.", error_detail=e)

