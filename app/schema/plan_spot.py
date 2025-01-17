import enum
from pydantic import BaseModel

from schema.plan_common import PlanCommon

class SpotType(enum):
    HISTORICAL = "역사"
    NATURAL = "자연"
    CULTURAL = "문화"
    ENTERTAINMENT = "엔터"
    SHOPPING = "쇼핑"
    FOOD_STREET = "먹자 골목"
    SPORTS = "스포츠"
    LEISURE = "레저"
    RELIGIOUS = "종교"
    WELLNESS = "웰빙"
    FESTIVAL = "축제"

class Spot(BaseModel, PlanCommon):
    id: int
    spot_type: SpotType
    phone_number: str
    business_status: str  # 영업 상태
    business_hours: str  # 영업 시간