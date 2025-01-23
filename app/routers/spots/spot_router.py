from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.repository.db import get_session_sync
from app.data_models.data_model import Spot
from app.services.spots.spot_service import reg_spot

router = APIRouter()

# 일정 저장
@router.post("/")
async def create_spot(spot: Spot, session: Session = Depends(get_session_sync)):
    try:
        reg_spot(spot, session)
        return {"message": "Spot saved successfully", "spot": spot}
    except Exception as e:
        print(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while creating the spot")

    
