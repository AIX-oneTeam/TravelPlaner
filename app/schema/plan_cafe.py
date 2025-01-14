import enum
from pydantic import BaseModel

from schema.plan_common import PlanCommon

class CafeType(enum):
    BAKERY = "베이커리"
    SANDWICH = "샌드위치"
    CAKE = "케이크"
    COOKIE = "쿠키"
    TAKEOUT = "테이크아웃"
    DINE_IN = "내부 이용"
    DRIVE_THRU = "드라이브스루"
    URBAN = "도시형 카페"
    OUTDOOR = "야외 카페"
    ROOFTOP = "옥상 카페"
    VEGAN = "비건 카페"
    PET_FRIENDLY = "반려동물 동반 카페"
    FULL_HOURS = "24시간 카페"

class Cafe(BaseModel, PlanCommon):
    id: int
    cafe_types: list[CafeType]
    phone_number: str
    business_status: str  # 영업 상태
    business_hours: str  # 영업 시간

