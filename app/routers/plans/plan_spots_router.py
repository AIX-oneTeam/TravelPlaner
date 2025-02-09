
from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.dtos.common.response import ErrorResponse, SuccessResponse
from app.services.plans.plan_spots_service import find_plan_spots
from app.repository.db import get_session_sync

router = APIRouter()


@router.get("/{plan_id}")
async def read_plan_spots(plan_id: int, session: Session = Depends(get_session_sync)):
    try:
        plan_spots = find_plan_spots(plan_id, session)
        return SuccessResponse(data=plan_spots, message="일정과 장소 정보가 성공적으로 조회되었습니다.")
    except Exception as e:
        return ErrorResponse(message="일정과 장소정보 조회에 실패했습니다.", error_detail=e)

