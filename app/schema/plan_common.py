from datetime import datetime
from pydantic import BaseModel

from schema.address import Address

class PlanCommon(BaseModel):
    id: int
    kor_name: str # 이름
    eng_name: str # 영문 이름
    tag: list # 태그
    description: str # 설명
    address: Address # 실제 주소
    url: str # 웹페이지 주소
    image_url: str # 이미지 주소
    map_url: str # 지도 주소
    likes: int # 좋아요 수
    satisfaction: float  # 만족도

    created_at: datetime
    updated_at: datetime
    