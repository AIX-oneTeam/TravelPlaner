from pydantic import BaseModel
from typing import List
from fastapi import APIRouter
from app.services.agents.accommodation_agent_e import run

router = APIRouter()

#입력 받을 사용자 데이터 정의
class UserInputData(BaseModel) :
    location : str
    check_in_date : str
    check_out_date: str
    concepts: List[str]
    
    
async def recommand_accommodation(userinput : UserInputData):
    return run(
        "location" : "userinput,
        
        
    )

