from datetime import time
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from requests import request
from app.repository.db import get_session_sync
from sqlmodel import Session
from app.data_models.data_model import Plan, Spot
from app.dtos.common.response import ErrorResponse, SuccessResponse
from app.repository.members.mebmer_repository import get_memberId_by_email
from app.repository.plans.plan_spots_repository import save_plan_spots
from app.services.plans.plan_service import edit_plan, find_member_plans, reg_plan
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

class PlanRequest(BaseModel):
    plan: Plan
    spots: list[spot_request]
    email: str

# 일정 저장
@router.post("/")
def create_plan(request_data: PlanRequest, request: Request, session: Session = Depends(get_session_sync)):
    try:
        # 0. memberid 획득
        if(request.state.user is not None):
            print("request.state.user : ", request.state.user)
            member_email = request.state.user.get("email")
            member_id = get_memberId_by_email(member_email, session)
        else:
            print("[ plan_router ] request_data.email : ", request_data.email)
            member_id = get_memberId_by_email(request_data.email, session)
            print("[ plan_router ] member_id : ", member_id)

        # 1. 일정 저장
        plan_id = reg_plan(request_data.plan, member_id, session)
        # 2. 장소 저장
        for spot in request_data.spots:
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
# 회원의 모든 일정 리스트 조회
@router.get("/")
async def read_member_plans(request: Request, session: Session = Depends(get_session_sync)):
    try:
        if(request.state.user is not None):
            member_email = request.state.user.get("email")
            member_id = get_memberId_by_email(member_email, session)
        else:
            return ErrorResponse(message="로그인이 필요합니다.")
        plans = find_member_plans(member_id, session)
        return SuccessResponse(data=plans, message="멤버의 일정 정보가 성공적으로 조회되었습니다.")
    except Exception as e:
        return ErrorResponse(message="멤버의 일정정보 조회에 실패했습니다.", error_detail=e)

# 일정 수정
@router.post("/{plan_id}")
async def update_plan(plan_id: int, request_data: PlanRequest, request: Request, session: Session = Depends(get_session_sync)):
    try:
        # 0. memberid 획득
        if(request.state.user is not None):
            member_email = request.state.user.get("email")
            member_id = get_memberId_by_email(member_email, session)
        else:
            member_id = get_memberId_by_email(request_data.email, session)
        
        # 1. 일정 수정
        edit_plan(plan_id, request_data.plan, member_id, session)
        return SuccessResponse(data={"plan_id": plan_id}, message="일정이 성공적으로 수정되었습니다.")
    except Exception as e:


        return ErrorResponse(message="일정 수정에 실패했습니다.", error_detail=e)


