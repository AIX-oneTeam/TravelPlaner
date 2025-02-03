from fastapi import Depends
from sqlmodel import Session
from app.data_models.data_model import Plan
from datetime import datetime

# plan을 저장하고 id를 반환함. (CQS 고려하지 않음.)
def save_plan(plan: Plan, session: Session):
    try:
        # ISO 형식의 문자열을 datetime 객체로 변환 후 MySQL 형식으로 변환
        start_date = datetime.fromisoformat(plan.start_date.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(plan.end_date.replace('Z', '+00:00'))
        
        plan.start_date = start_date
        plan.end_date = end_date
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

   
