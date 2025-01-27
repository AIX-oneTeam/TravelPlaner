
from datetime import time
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.repository.db import get_session_sync

from app.data_models.data_model import Plan, Spot
from app.dtos.common.response import ErrorResponse, SuccessResponse
from app.repository.plans.plan_spots_repository import save_plan_spots
from app.services.plans.plan_service import reg_plan
from app.services.spots.spot_service import reg_spot


router = APIRouter()

class spot_request(BaseModel):
    kor_name: str = Field(max_length=255)
    eng_name: str | None = Field(default=None, max_length=255)
    description: str = Field(max_length=255)
    address: str = Field(max_length=255)
    zip: str = Field(max_length=10)
    url: str | None = Field(default=None, max_length=2083)
    image_url: str = Field(max_length=2083)
    map_url: str = Field(max_length=2083)
    likes: int | None = None
    satisfaction: float | None = None
    spot_category: int
    phone_number: str | None = Field(default=None, max_length=300)
    business_status: bool | None = None
    business_hours: str | None = Field(default=None, max_length=255)

    order: int
    day_x: int
    spot_time: time | None = None

# 일정 저장
@router.post("/")
def create_plan(plan: Plan, Spots:list[spot_request], member_id: int, session: Session = Depends(get_session_sync)):

    try:
        # 0. 트랜잭션 생성
        # 1. 일정 저장
        plan_id = reg_plan(plan, member_id, session)
        # 2. 장소 저장
        for spot in Spots:
            spot_id = reg_spot(Spot( #SQL Model
                kor_name=spot.kor_name,
                eng_name=spot.eng_name,
                description=spot.description,
                address=spot.address,
                zip=spot.zip,
                url=spot.url,
                image_url=spot.image_url,
                map_url=spot.map_url,
                likes=spot.likes,
                satisfaction=spot.satisfaction,
                spot_category=spot.spot_category,
                phone_number=spot.phone_number,
                business_status=spot.business_status,
                business_hours=spot.business_hours
            ), session)
            # 3. 일정-장소 매핑 저장
            save_plan_spots(plan_id, spot_id, spot.order, spot.day_x, spot.spot_time, session)
        return SuccessResponse(data={"plan_id": plan_id}, message="일정이 성공적으로 등록되었습니다.")
    except Exception as e:
        return ErrorResponse(message="일정 등록에 실패했습니다.", error_detail=e)

# 일정 조회