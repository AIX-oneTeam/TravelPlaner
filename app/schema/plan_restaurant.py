import enum
from pydantic import BaseModel

from schema.plan_common import PlanCommon

class RestaurantType(enum):
    KOREAN = "한식"
    CHINESE = "중식"
    JAPANESE = "일식"
    WESTERN = "양식"
    ASIAN = "아시아식"
    FASTFOOD = "패스트푸드"
    FUSION = "퓨전"
    BAKERY = "베이커리"
    PUB = "펍"
    BUFFET = "뷔페"
    VEGETARIAN = "채식"
    SEAFOOD = "해산물"
    STREET_FOOD = "길거리 음식"
    FINE_DINING = "고급 요리"
    FAMILY_STYLE = "가족 스타일"
    STEAKHOUSE = "스테이크 하우스"

class Cafe(BaseModel, PlanCommon):
    id: int
    restaurant_type: RestaurantType
    phone_number: str
    business_status: str  # 영업 상태
    business_hours: str  # 영업 시간