from fastapi import Depends
from app.repository.regions.region_repository import (
    get_all_divisions,
)
from sqlmodel import Session

# 모든 행정구역 데이터 가져오기
def get_all_divisions_service(session: Session):
    return get_all_divisions(session)
