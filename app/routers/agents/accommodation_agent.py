from pydantic import BaseModel
from typing import List
from fastapi import APIRouter
import asyncio
from app.services.agents.accommodation_agent_3 import run

router = APIRouter()

#입력 받을 사용자 데이터 형식
class UserInputData(BaseModel) :
    location : str
    check_in_date : str
    check_out_date: str

#전달 데이터 형식
class AccommodationResponse(BaseModel):
    name: str
    address: str
    phone_number: str
    review_keywords: List[str]

@router.post("/accommodations")
async def get_accommodations(user_input:UserInputData) :
    """
    숙소 추천 API
    """
    try:
        #asyncio.to_thread() -> 별도 스레드에서 실행하는 비동기 처리
        result = await asyncio.to_thread(
            run,                                #실생할 함수
            location = user_input.location,     # 함수 전달 데이터
            check_in_date = user_input.check_in_date,
            check_out_date = user_input.check_out_date
        )
        return {
            "status" :  "200",
            "data" : result
        }
    except Exception as e:
        return  f"[숙소 추천 API] 에러: {str(e)}"

