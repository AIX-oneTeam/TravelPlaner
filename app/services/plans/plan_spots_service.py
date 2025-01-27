
from app.utils.serialize_time import serialize_time
from app.repository.plans.plan_spots_repository import get_plan_spots
from sqlmodel import Session

def find_plan_spots(plan_id: int, session: Session):
    plan_spots_with_spot_info = get_plan_spots(plan_id, session)
    
    #  day_x와 order 순으로 정렬
    plan_spots_with_spot_info[1].sort(
        key=lambda item: (item["plan_spot"].day_x, item["plan_spot"].order)
    )

    #  Plan 데이터 직렬화
    plan_spots_with_spot_info[0]["plan"] = serialize_time(
        plan_spots_with_spot_info[0]["plan"], 
        ["start_date", "end_date", "created_at", "updated_at"]
    )

    # PlanSpotMap과 Spot 데이터 직렬화
    for item in plan_spots_with_spot_info[1]:
        item["plan_spot"] = serialize_time(
            item["plan_spot"], ["spot_time"]
        )
        item["spot"] = serialize_time(
            item["spot"], ["created_at", "updated_at"]
        )
    return plan_spots_with_spot_info
