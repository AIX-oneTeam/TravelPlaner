import enum
from pydantic import BaseModel

from schema.plan_common import PlanCommon

class RestaurantType(enum):
    KOREAN = "한식"
    CHINESE = "중식"
    JAPANESE = "일식"
    WESTERN = "양식"
    MAXCIAN = "멕시칸"
    ITALIAN = "이탈리안"
    THAI = "태국"
    VIETNAMESE = "베트남"
    INDIAN = "인도"
    MIDDLE_EASTERN = "중동"
    FASTFOOD = "패스트푸드"
    FUSION = "퓨전"
    PUB = "펍"
    BUFFET = "뷔페"
    VEGETARIAN = "채식"
    SEAFOOD = "해산물"
    FINE_DINING = "고급 요리"
    FAMILY_STYLE = "가족 스타일"
    STEAKHOUSE = "스테이크 하우스"

class Cafe(BaseModel, PlanCommon):
    id: int
    restaurant_type: RestaurantType
    phone_number: str
    business_status: str  # 영업 상태
    business_hours: str  # 영업 시간