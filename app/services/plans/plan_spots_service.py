
from sqlmodel import Session
from app.data_models.data_model import Spot
from datetime import datetime

from app.utils.serialize_time import serialize_time
from app.repository.plans.plan_spots_repository import get_plan_spots

def find_plan_spots(plan_id: int, request):
    plan_spots = get_plan_spots(plan_id, request)
    serialized_plan_spots = [serialize_time(plan_spot,  ["spot_time"]) for plan_spot in plan_spots]
    sorted_plan_spots = sorted(
        serialized_plan_spots,
        key=lambda spot: (spot["day_x"], spot["order"])  # day_x → order 순으로 정렬
    )
    print(sorted_plan_spots)
    return sorted_plan_spots
