from sqlmodel import Session, select
from app.data_models.data_model import PlanSpotMap, Spot

def save_plan_spots (plan_id:int, spot_id:int, order:int, day_x:str, spot_time:str,  request):
    try:
        engine = request.app.state.engine
        with Session(engine) as session:
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

def get_plan_spots(plan_id: int, request):
    try:
        engine = request.app.state.engine
        with Session(engine) as session:
            
            stmt = (
                select(PlanSpotMap, Spot)
                .join(Spot, PlanSpotMap.spot_id == Spot.id)  
                .where(PlanSpotMap.plan_id == plan_id)  
            )
            result = session.exec(stmt).all() 

            plan_spots_with_spot_info = [
                {
                    "plan_spot": plan_spot,
                    "spot": spot
                }
                for plan_spot, spot in result
            ]

            return plan_spots_with_spot_info if plan_spots_with_spot_info is not None else None
    except Exception as e:
        print("[ planRepository ] get_plan_spots() 에러 : ", e)

