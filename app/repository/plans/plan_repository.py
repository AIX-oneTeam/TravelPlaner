from fastapi import Depends
from sqlmodel import Session
from app.data_models.data_model import Plan
from app.repository.db import get_session_sync

# plan을 저장하고 id를 반환함. (CQS 고려하지 않음.)
def save_plan(plan: Plan, request):
    try:
        engine = request.app.state.engine
        with Session(engine) as session:
            session.add(plan)
            session.commit()
            return plan.id
    except Exception as e:
        print("[ planRepository ] save_plan() 에러 : ", e)


def get_plan(plan_id: int, request):
    try:
        engine = request.app.state.engine
        with Session(engine) as session:
            plan = session.get(Plan, plan_id)
            return plan if plan is not None else None
    except Exception as e:
        print("[ planRepository ] get_plan() 에러 : ", e)

   
