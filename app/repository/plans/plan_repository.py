from fastapi import Depends
from sqlmodel import Session
from app.data_models.data_model import Plan

# plan을 저장하고 id를 반환함. (CQS 고려하지 않음.)
def save_plan(plan: Plan, session: Session):
    try:
        session.add(plan)
        session.flush()
        print("[ plan_repository ] new_plan.id : ", plan.id)
        session.commit()
        return plan.id
    except Exception as e:
        print("[ plan_repository ] save_plan() 에러 : ", e)
        raise e


def get_plan(plan_id: int, session: Session):
    try:
        plan = session.get(Plan, plan_id)
        return plan if plan is not None else None
    except Exception as e:
        print("[ plan_repository ] get_plan() 에러 : ", e)
        raise e

   
