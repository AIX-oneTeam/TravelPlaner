from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.data_models.data_model import Spot
from app.dtos.common.response import ErrorResponse, SuccessResponse
from app.services.spots.spot_service import reg_spot, find_spot
from app.repository.db import get_session_sync

router = APIRouter()

# 일정 저장
@router.post("")
async def create_spot(spot: Spot, session: Session = Depends(get_session_sync)):
    try:
        spot_id = reg_spot(spot, session)
        return SuccessResponse(data={"spot_id": spot_id}, message="장소가 성공적으로 등록되었습니다.")
    except Exception as e:
        return ErrorResponse(message="일정 등록에 실패했습니다.", error_detail=e)

# 일정 조회    
@router.get("/{spot_id}")
async def read_spot(spot_id: int, session: Session = Depends(get_session_sync)):
    try:
        spot = find_spot(spot_id, session)
        return SuccessResponse(data={"spot": spot}, message="장소가 성공적으로 조회되었습니다.")
    except Exception as e:
        return ErrorResponse(message="등록되지 않은 장소입니다.", error_detail=e)
    