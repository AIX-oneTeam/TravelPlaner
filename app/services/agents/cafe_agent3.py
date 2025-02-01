from crewai import Agent, Task, Crew, LLM, Process
from crewai_tools import SerperDevTool
from naver_place_tool import naver_place_tool
from pydantic import BaseModel,Field
from typing import List
import os
from dotenv import load_dotenv
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# LLM 초기화
my_llm = LLM(
    model="gpt-4o",
    api_key=OPENAI_API_KEY,
    temperature=0,
    max_tokens=4000
)


class Cafe(BaseModel):
    """ 카페 정보 """
    kor_name: str =  Field(..., description="카페 이름")
    eng_name: str =  Field(..., description="카페 이름 (영문)")
    description: str =  Field(..., description="카페 주요 특징, 분위기, 시그니처 메뉴")
    address: str =  Field(..., description="카페 도로명 주소")
    zip: str =  Field(..., description="카페 우편번호")
    url: str =  Field(..., description="카페 대표 홈페이지 url")
    image_url: str =  Field(..., description="카페 대표 이미지 url")
    map_url: str =  Field(..., description="카페 지도 url(google, naver, kakao 중 택1)")
    phone_number: str =  Field(description="카페 전화번호")
    business_status: str =  Field(..., description="폐업유무(bool)")
    business_hours: str =  Field(..., description="운영 시간")
    parking: str =  Field(..., description="주차 가능여부(bool)")
    pet_friendly: str =  Field(..., description="애견동반 가능여부(bool)")

class CafeList(BaseModel):
    cafes: List[Cafe]

search_tool = SerperDevTool()
# 에이전트 정의

researcher = Agent(
    role="카페 정보 검색 및 분석 전문가",
    goal="고객 선호도를 분석해 최적의 카페 정보 수집 후 각 카페의 주요 특징 분석",
    backstory="""
    사용자의 여행을 특별하게 만들기 위해, 최적의 카페를 찾고 카페의 매력을 심층 분석하여 사용자가 최적의 선택을 할 수 있도록 돕는 전문가
    고객의 선호도 및 제약 사항(애견 동반 유무, 주차 등)을 반드시 반영해야 합니다.
    협찬을 받거나 광고성 글은 제외하고 조사해주세요.
    모르는 정보는 "정보 없음"으로 나타내세요.
    각 cafe는 모두 다른 곳으로 조사해주세요.
    """,
    tools=[search_tool],
    allow_delegation=False,
    max_iter=2,
    llm=my_llm,
    verbose=True
)

ranker = Agent(
    role="카페 검증 및 추천 전문가",
    goal="researcher가 분석한 데이터를 기반으로 사용자 조건에 맞는지 검증하고, 적합한 카페 3곳을 선정합니다.",
    backstory="사용자 입력을 기반으로 가장 적합한 카페를 정밀하게 선정하는 평가 전문가. 자료 미흡시 researcher에게 자료 보완을 요구합니다. 3곳의 cafe는 모두 다른 곳으로 선택해주세요.",
    max_iter=2,
    tools=[search_tool],
    llm=my_llm,
    verbose=True
)

# 태스크 정의
researcher_task = Task(
    description="""
    고객이 최고의 여행을 할 수 있도록 고객의 상황과 취향에 맞는 카페를 찾고 카페 정보를 반환해주세요.

    카페는 반드시 고객의 여행 지역인 {location}에 위치해야하고, 폐업 또는 휴업하지 않은 카페여야합니다. 
    고객의 선호도({concepts})에 적합하고, 주 연령대({age})가 주로 선호하는 카페를 찾아주세요.
    주차 가능 여부({parking})와 애견동반 여부({pet_friendly})를 반드시 반영해주세요.
    애견동반 여부가 False일 경우 검색어에 "애견"이라는 단어를 포함하지 마세요.
    주차 가능 여부가 False일 경우 검색어에 "주차"라는 단어를 포함하지 마세요. 
    고객의 선호도({concepts})에 "프랜차이즈"가 포함되지 않는 경우, 프랜차이즈 카페는 제외하고 찾아주세요.
    프랜차이즈 카페 : 스타벅스, 투썸플레이스, 이디야, 빽다방, 메가커피 등 전국에 매장이 5개 이상인 커피 전문점 
    협찬을 받고 작성한 글이나 광고 글은 제외하고 조사해주세요.
    시그니처 메뉴는 "다양한"과 같은 추상적인 단어를 사용하지 않고 정확한 메뉴의 이름을 명시해주세요.
    description에는 카페의 최신 리뷰와 사진을 분석해 해당 카페의 분위기, 시그니처 메뉴, 사람들이 공통적으로 좋아했던 주요 특징을 간략히 적어주세요.
    description에는 나이, 연령대에 대한 언급 하지마세요.
    url에는 출처가 아닌, 해당 카페의 공식 홈페이지 주소를 입력해주세요.
    image_url은 해당 카페의 리뷰에 사람들이 등록한 이미지url 주소를 입력해주세요. 
    phone_number의 경우 카페의 대표 전화번호를 입력해주세요.
    business_hours의 경우 여러 일자로 나누어져 있으면, 띄어쓰기로 구분하여 모두 추가해주세요.
    모르는 정보는 지어내지 말고 "정보 없음"으로 작성하세요. 
    
    최소 5개 이상의 cafe 정보를 반환하세요. 반환값은 모두 다른 카페로 찾아주세요.
    """,
    expected_output="조사한 카페의 정보를 json 형태로 출력해주세요.",
    output_json=CafeList,
    agent=researcher,
)

ranker_task = Task(
    description="""
    고객이 최고의 여행을 할 수 있도록 researcher가 조사한 카페 중 고객의 조건에 가장 적합한 카페 3곳을 선정하고 해당 카페 정보를 반환해주세요.  
    tool을 이용해 researcher가 알려준 카페 이름을 검색하고, researcher가 작성한 내용에 오류가 없는지 검증하고 잘못 작성한 정보는 수정해주세요.
    
    researcher가 수행한 결과를 토대로 아래의 항목과 일치하는지 확인하고, 일치하지 않으면 researcher에게 다시 자료 조사를 시키세요.
    카페는 반드시 고객의 여행 지역인 {location}에 위치해야하고, 폐업 또는 휴업하지 않은 카페여야합니다. 
    고객의 선호도({concepts})에 적합하고, 주 연령대({age})가 주로 선호하는 카페여야합니다.
    고객이 요구한 주차 가능 여부({parking})와 애견동반 여부({pet_friendly})가 반드시 반영되야 합니다.
    카페의 분위기, 시그니처 메뉴, 주요 특징이 description에 반영되어 있어야 합니다. 
    """,
    expected_output="""고객에게 가장 적합한 카페 선정하고 반드시 3곳의 정보를 json 형태로 반환해주세요. {"cafes": [<Cafe1>, <Cafe2>, <Cafe3>]}""",
    output_json=CafeList,
    agent=ranker
)


# 멀티 에이전트 시스템 설정
crew = Crew(
    agents=[researcher, ranker],
    tasks=[researcher_task, ranker_task],
    verbose=True,
)

user_input = {
    "location":"성수동",  # 사용자의 지역
    "age" : "30대",
    "concepts":"아기자기한 분위기, 치즈 케이크가 맛있는 곳",  # 취향
    "parking":False,  # 주차 가능 여부
    "pet_friendly":False  # 반려동물 동반 가능 여부
}

# 실행
try:
    result = crew.kickoff(inputs=user_input)
    print(result)
except Exception as e:
    print(f"Error during execution: {e}")
