from fastapi import Depends
from sqlmodel import Session, select
from app.data_models.data_model import Plan
from datetime import datetime

from app.utils import serialize_time

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

# 회원의 모든 일정 리스트 조회
def get_member_plans(member_id: int, session: Session):
    try:
        result = session.exec(select(Plan).where(Plan.member_id == member_id)).all()
        # serialize_time 유틸리티를 사용하여 변환
        plans = [
            serialize_time.serialize_time(
                plan, 
                ['start_date', 'end_date', 'created_at', 'updated_at']
            )
            for plan in result
        ] if result is not None else None
        
        print("[ plan_repository ] get_member_plans() 결과 : ", plans)
        print("[ plan_repository ] get_member_plans() 결과 타입 : ", type(plans))
        return plans
    except Exception as e:
        print("[ plan_repository ] get_member_plans() 에러 : ", e)
        raise e

   
