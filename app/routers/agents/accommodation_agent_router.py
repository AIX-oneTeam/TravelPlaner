from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
import asyncio
from app.services.agents.accommodation_agent_4 import run
import json
from datetime import datetime
from app.services.agents.accommodation_agent_service import AccommodationAgentService

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
    prompt: Optional[str] = None


@router.post("/accommodations")
async def get_accommodations(user_input: TravelPlanRequest):
    """
    숙소 추천 API
    """
    try:
        start_time = datetime.now()

        instance = AccommodationAgentService()
        result = await instance.accommodation_agent(user_input.model_dump())

        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        if not result:
            print("결과값이 없습니다. 실행 시간: {execution_time:.4f}초")

            raise HTTPException(
                status_code=404,
                detail={
                    "status": "error",
                    "message": "카페 검색 결과가 없습니다.",
                    "execution_time": execution_time
                }
            )

        print(f"cafe_agent() 실행 시간: {execution_time:.4f}초")

        return {
            "status": "success",
            "message": "숙소 리스트가 생성되었습니다.",
            "data": result,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"숙소 추천 처리 중 오류가 발생했습니다: {str(e)}"
        )
