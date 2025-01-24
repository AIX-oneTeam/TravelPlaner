from fastapi import Depends, Request
from sqlmodel import Session, select
from app.data_models.data_model import AdministrativeDivision
from app.repository.db import get_session_sync

# 모든 행정구역 데이터 가져오기
def get_all_divisions(request: Request):
    try:
        engine = request.app.state.engine
        with Session(engine) as session:
            statement = select(AdministrativeDivision)
            results = session.exec(statement).all()
            return [
                {"city_province": r.city_province, "city_county": r.city_county}
                for r in results
            ]
    except Exception as e:
        print("[ administrativeDivisionRepository ] get_all_divisions() 에러 : ", e)
        return []
