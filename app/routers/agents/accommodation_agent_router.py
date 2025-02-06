from pydantic import BaseModel
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
import asyncio
from app.services.agents.accommodation_agent_3 import run
import json

router = APIRouter()

class UserInputData(BaseModel):
    location: str
    check_in_date: str
    check_out_date: str
    age_group: int
    adults: int
    children: int
    keyword: List[str]
  

@router.post("/accommodations")
async def get_accommodations(user_input: UserInputData):
    """
    숙소 추천 API
    """
    try:
        crew_output = await asyncio.to_thread(
            run,
            location=user_input.location,
            check_in_date=user_input.check_in_date,
            check_out_date=user_input.check_out_date,
            age_group=user_input.age_group,
            adults=user_input.adults,
            children=user_input.children,
            keyword=user_input.keyword
        )
        return {"accommodations": [accommodation.dict() for accommodation in crew_output]}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"[숙소 추천 API] 에러: {str(e)}")
