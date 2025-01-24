from app.data_models.data_model import Plan
from app.repository.plans.plan_repository import get_plan, save_plan


def reg_plan(plan: Plan, member_id: int, request):
    plan.member_id = member_id
    plan_id = save_plan(plan, request)

    return plan_id

def find_plan(plan_id: int, request):
    plan = get_plan(plan_id, request)
    return plan
