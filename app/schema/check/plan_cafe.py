import enum
from pydantic import BaseModel

from schema.plan_common import PlanCommon

class CafeType(enum):
    BAKERY = "베이커리"
    DESSERT = "디저트"
    CAKE = "케이크"
    TAKEOUT = "테이크아웃"
    DRIVE_THRU = "드라이브스루"
    LARGE = "대형 카페"
    SMALL = "소형 카페"
    TERRACE = "야외 카페"
    ROOFTOP = "옥상 카페"
    VEGAN = "비건 카페"
    PET_FRIENDLY = "반려동물 동반 카페"
    FULL_HOURS = "24시간 카페"
    BOOK_CAFE = "책카페"
    BOARD_GAME = "보드게임 카페"
    ALONE_CAFFE = "혼자 가기 좋은 카페"
    FRANCHISE = "프랜차이즈 카페"

class Cafe(BaseModel, PlanCommon):
    id: int
    cafe_types: list[CafeType]
    phone_number: str
    business_status: bool  # 폐업 상태
    business_hours: str  # 영업 시간



