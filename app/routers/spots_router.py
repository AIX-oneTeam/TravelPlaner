from fastapi import APIRouter


from app.data_models.spot import Spot
from app.services.spot_service import reg_spot

router = APIRouter()

# 일정 저장
@router.post("/spots")
async def create_spot(spot: Spot):
    reg_spot(spot)
    
    
