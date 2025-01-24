
from app.utils.serialize_time import serialize_time
from app.repository.plans.plan_spots_repository import get_plan_spots

def find_plan_spots(plan_id: int, request):
    plan_spots_with_spot_info = get_plan_spots(plan_id, request)
    
    #  day_x와 order 순으로 정렬
    plan_spots_with_spot_info.sort(
        key=lambda item: (item["plan_spot"].day_x, item["plan_spot"].order)
    )

    # 직렬화 
    for item in plan_spots_with_spot_info:
        item["plan_spot"] = serialize_time(
            item["plan_spot"], ["spot_time"]
        )
        item["spot"] = serialize_time(
            item["spot"], ["created_at", "updated_at"]
        )
    return plan_spots_with_spot_info