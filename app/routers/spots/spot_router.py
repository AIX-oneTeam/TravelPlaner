from fastapi import APIRouter, Request

from app.data_models.data_model import Spot
from app.dtos.common.response import ErrorResponse, SuccessResponse
from app.services.spots.spot_service import reg_spot, find_spot

router = APIRouter()

# 일정 저장
@router.post("/")
async def create_spot(spot: Spot, request: Request):
    try:
        spot_id = reg_spot(spot, request)
        return SuccessResponse(data={"spot_id": spot_id}, message="장소가 성공적으로 등록되었습니다.")
    except Exception as e:
        return ErrorResponse(message="일정 등록에 실패했습니다.", error_detail=e)

# 일정 조회    
@router.get("/{spot_id}")
async def read_spot(spot_id: int, request: Request):
    try:
        spot = find_spot(spot_id, request)
        return SuccessResponse(data={"spot": spot}, message="장소가 성공적으로 조회되었습니다.")
    except Exception as e:
        return ErrorResponse(message="장소 조회에 실패했습니다.", error_detail=e)
    