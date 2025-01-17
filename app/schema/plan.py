from datetime import datetime
import enum
from typing import Dict
from pydantic import BaseModel

"""
__summary__: 동행인 타입을 나타내는 열거형입니다.
"""
class CompanionType(enum):
    adult = "성인"
    teen = "청소년"
    child = "어린이"
    infant = "영유아"
    pet = "반려견"
    senior = "시니어"

"""
__summary__: 연령대 타입을 나타내는 열거형입니다.
"""
class AgeType(enum):
    teen = "10대"
    twenties = "20대"
    thirties = "30대"
    forties = "40대"
    fifties = "50대"
    sixties = "60대"
    seventies = "70대"
    eighties = "80대"


"""
__summary__: 여행 일정 스키마입니다. 식별자는 id입니다.
__description__: 여행 일정은 회원과 N:1 관계를 가집니다.
"""
class Plan(BaseModel):
    # 입력 데이터
    id: int
    plan_name: str # 일정명
    start_date: datetime # 시작일
    end_date: datetime # 종료일
    main_location: str # 주요 여행지
    ages: AgeType # 평균 주요 연령
    companion_count: Dict[CompanionType, int] # 동행인 수
    plan_concepts: dict # 일정 컨셉

    # 외래키
    check_list_id: int # 체크리스트 1:1 관계
    member_id: int # 작성자 id
    plan_elements_id: list[int] # 일정 요소 1:N 관계

    # DB 관리 데이터
    created_at: datetime
    updated_at: datetime