from app.data_models.data_model import Plan
from app.repository.plans.plan_repository import get_member_plans, get_plan, save_plan
from sqlmodel import Session

def reg_plan(plan: Plan, member_id: int, session: Session):
    print("[ plan_service ] member_id : ", member_id)  # 디버깅용
    plan.member_id = member_id
    print("[ plan_service ] plan.member_id : ", plan.member_id)  # 디버깅용
    plan_id = save_plan(plan, session)
    return plan_id

def edit_plan(plan_id: int, plan: Plan, member_id: int, session: Session):
    plan.member_id = member_id
    plan_id = save_plan(plan, session, plan_id)
    return plan_id

def find_plan(plan_id: int, session: Session):
    plan = get_plan(plan_id, session)

    return plan

def find_member_plans(member_id: int, session: Session):
    plans = get_member_plans(member_id, session)
    return plans

