from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from app.services.agents.site_agent import create_tourist_plan
from app.services.agents.cafe_agent_service import cafe_agent
from app.services.agents.restaurant_agent_service import create_recommendation
from app.services.agents.travel_all_schedule_agent_service import create_plan

router = APIRouter()

class Companion(BaseModel):
    label: str
    count: int

class TravelPlanRequest(BaseModel):
    ages: str
    companion_count: List[Companion]
    start_date: str
    end_date: str
    concepts: List[str]
    main_location: str
    prompt: Optional[str] = Field(default=None)

@router.post("/plan")
async def generate_plan(
    user_input: TravelPlanRequest,
    agent_type: List[str] = Query(..., alias="agent_type[]")):

    try:
        print("프론트에서 받은 데이터:", user_input)
        
        input_dict = user_input.model_dump()
        input_dict["agent_type"] = agent_type  

        restaurant_result = create_recommendation(input_dict)
        site_result = create_tourist_plan(input_dict)
        cafe_result = await cafe_agent(input_dict)  # 만약 async라면 직접 await

        external_data ={
            "restaurant":restaurant_result,
            "site" :site_result,
            "cafe" :cafe_result
        }
        user_input["external_data"] = external_data


        print("Python dict 변환:", input_dict)

        #최종 함수 호출 
        result = await create_plan(input_dict)

        return {
            "status": "success",
            "message": "일정과 장소 리스트가 생성되었습니다.",
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
