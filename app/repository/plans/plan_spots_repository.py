from sqlmodel import Session

from app.data_models.data_model import PlanSpotMap


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