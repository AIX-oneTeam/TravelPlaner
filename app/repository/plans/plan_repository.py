from fastapi import Depends
from sqlmodel import Session, select
from app.data_models.data_model import Plan
from datetime import datetime

from app.utils import serialize_time

# plan을 저장하거나 수정하고 id를 반환함. (CQS 고려하지 않음.)
def save_plan(plan: Plan, session: Session, plan_id: int = None):
    try:
        # ISO 형식의 문자열을 datetime 객체로 변환 후 MySQL 형식으로 변환
        start_date = datetime.fromisoformat(plan.start_date.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(plan.end_date.replace('Z', '+00:00'))
        
        plan.start_date = start_date
        plan.end_date = end_date
        
        if plan_id:
            # 기존 plan 조회
            existing_plan = session.get(Plan, plan_id)
            if existing_plan is None:
                raise ValueError(f"ID가 {plan_id}인 Plan을 찾을 수 없습니다.")
            
            # 기존 plan 업데이트
            existing_plan.name = plan.name
            existing_plan.start_date = plan.start_date
            existing_plan.end_date = plan.end_date
            existing_plan.main_location = plan.main_location
            existing_plan.ages = plan.ages
            existing_plan.companion_count = plan.companion_count
            existing_plan.concepts = plan.concepts
            existing_plan.updated_at = datetime.now()
            session.add(existing_plan)
            print("[ plan_repository ] plan 업데이트 완료 : ", plan_id)
        else:
            # 새로운 plan 생성
            session.add(plan)
            session.flush()
            plan_id = plan.id
            print("[ plan_repository ] 새로운 plan 생성 완료 : ", plan_id)
            
        session.commit()
        return plan_id
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

   
