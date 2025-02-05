from pydantic import BaseModel
from typing import List
from fastapi import APIRouter
import asyncio
from app.services.agents.accommodation_agent_3 import run
import json

router = APIRouter()

#입력 받을 사용자 데이터 형식
class UserInputData(BaseModel) :
    location : str
    check_in_date : str
    check_out_date: str
    age_group : int
    adults : int
    children:int
    keyword: List[str]
    
#전달 데이터 형식
class AccommodationResponse(BaseModel):
    name: str
    address: str
    phone_number: str
    review_keywords: List[str]

@router.post("/accommodations")
async def get_accommodations(user_input: UserInputData):
    """
    숙소 추천 API
    """
    try:
        result = await asyncio.to_thread(
            run,
            location=user_input.location,
            check_in_date=user_input.check_in_date,
            check_out_date=user_input.check_out_date,
            age_group=user_input.age_group,
            adults=user_input.adults,
            children=user_input.children,
            keyword=user_input.keyword
        )
        
        # Parse the JSON string, then re-serialize it without indentation
        parsed_result = json.loads(result)
        single_line_json = json.dumps(parsed_result, separators=(',', ':'))
        
        return {
            "status": "200",
            "data": single_line_json
        }
    except Exception as e:
        return f"[숙소 추천 API] 에러: {str(e)}"

