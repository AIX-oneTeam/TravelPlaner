from fastapi import Depends
from sqlmodel import Session
from app.data_models.plan import Plan
from app.repository.db import get_session_sync

# plan을 저장하고 id를 반환함. (CQS 고려하지 않음.)
def save_plan(plan: Plan, session: Session = Depends(get_session_sync)):
    session.add(plan)
    session.commit()

    return plan.plan_id

def get_plan(plan_id: int, session: Session = Depends(get_session_sync)):
    plan = session.get(Plan, plan_id)
    # TODO: 예외처리 필요. Optional같은 객체가 있나?
    return plan
