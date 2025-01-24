from fastapi import Depends
from sqlmodel import Session, select
from app.data_models.data_model import Plan, PlanSpotMap
from app.repository.db import get_session_sync

def get_plan_spots(plan_id: int, request):
    try:
        engine = request.app.state.engine
        with Session(engine) as session:
            query = select(PlanSpotMap).where(PlanSpotMap.plan_id == plan_id)
            plan_spots = session.exec(query).all()
            return plan_spots if plan_spots is not None else None
    except Exception as e:
        print("[ planRepository ] get_plan_spots() 에러 : ", e)

