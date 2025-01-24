
from sqlmodel import Session
from app.data_models.data_model import Spot
from app.repository.spots.spot_repository import save_spot, get_spot

def reg_spot(spot: Spot, session: Session):
    spot_id = save_spot(spot,session)
    return spot_id

def find_spot(spot_id: int, request):
    spot = get_spot(spot_id, request)
    return spot