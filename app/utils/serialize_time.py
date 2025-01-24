from datetime import time, date, datetime
from sqlmodel import SQLModel

def serialize_time(
    model: SQLModel, time_fields: list[str]
) -> dict:
    """
    SQLModel 객체에서 지정된 날짜 및 시간 필드를 ISO 8601 문자열로 변환.

    Args:
        model (SQLModel): SQLModel 객체.
        time_fields (list[str]): 변환할 날짜/시간 필드 이름의 리스트.

    Returns:
        dict: 변환된 데이터 딕셔너리.
    """
    data = model.model_dump()  # SQLModel 객체를 dict로 변환
    for field in time_fields:
        if field in data and isinstance(data[field], (time, date, datetime)):
            # date 또는 datetime 타입이면 ISO 포맷으로 변환
            data[field] = data[field].isoformat()
    return data
