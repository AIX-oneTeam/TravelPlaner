from sqlmodel import Session, select
from app.data_models.data_model import PlanSpotMap, Plan, Spot

def save_plan_spots (plan_id:int, spot_id:int, order:int, day_x:str, spot_time:str, session:Session):
    try:
        session.add(PlanSpotMap(
            plan_id=plan_id,
            spot_id=spot_id,
            order=order,
            day_x=day_x,
            spot_time=spot_time
            ))
        session.commit()
    except Exception as e:
        print("[ planSpotRepository ] save_plan_spots() 에러 : ", e)
        raise e

def get_plan_spots(plan_id: int, session:Session):
    try:
        plan_stmt = select(Plan).where(Plan.id == plan_id)
        plan = session.exec(plan_stmt).first()

        spot_stmt = (
            select(PlanSpotMap, Spot)
            .join(Spot, PlanSpotMap.spot_id == Spot.id)  
            .where(PlanSpotMap.plan_id == plan_id)  
        )
        spots = session.exec(spot_stmt).all() 

        plan_spots_with_spot_info = {
            "plan": plan,
            "detail" : [
            {
                "plan_spot": plan_spot,
                "spot": spot
            }
            for plan_spot, spot in spots
        ]}

        session.commit()
        return plan_spots_with_spot_info if plan_spots_with_spot_info is not None else None
    except Exception as e:
        print("[ planRepository ] get_plan_spots() 에러 : ", e)


