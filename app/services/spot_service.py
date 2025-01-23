from app.data_models.spot import Spot
from app.repository.spots.spot_repository import save_spot

def reg_spot(spot: Spot):
    save_spot(spot)
