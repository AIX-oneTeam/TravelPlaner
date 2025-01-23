from app.data_models.data_model import Plan
from app.repository.plans.plan_repository import save_plan


def reg_plan(plan: Plan, member_id: int):
    plan.member_id = member_id
    plan_id = save_plan(plan)

    return plan_id
