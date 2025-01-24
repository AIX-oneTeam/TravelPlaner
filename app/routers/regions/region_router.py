from fastapi import APIRouter, Request
from app.dtos.common.response import ErrorResponse, SuccessResponse
from app.services.regions.regions_service import (
    get_all_divisions_service,
)

router = APIRouter()

# 모든 행정구역 데이터 조회
@router.get("/all")
def fetch_all_divisions(request: Request):
    try:
        # 서비스 호출
        divisions = get_all_divisions_service(request)
        return SuccessResponse(
            data={"divisions": divisions},
            message="전체 지역 정보가 성공적으로 조회되었습니다.",
        )
    except Exception as e:
        return ErrorResponse(
            message="전체 지역 정보를 조회하는 데 실패했습니다.", error_detail=str(e)
        )
