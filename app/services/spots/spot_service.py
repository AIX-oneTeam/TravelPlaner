
from sqlmodel import Session
from app.data_models.data_model import Spot
from app.repository.spots.spot_repository import save_spot

def reg_spot(spot: Spot, session: Session):
    save_spot(spot,session)
