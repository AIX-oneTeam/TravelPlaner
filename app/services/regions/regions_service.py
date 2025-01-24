from fastapi import Request
from app.repository.regions.region_repository import (
    get_all_divisions,
)

# 모든 행정구역 데이터를 가져오기
def get_all_divisions_service(request: Request):
    return get_all_divisions(request)
