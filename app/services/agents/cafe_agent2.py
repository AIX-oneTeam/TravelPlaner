from crewai import Agent, Task, Crew, LLM, Process
from naver_place_tool import naver_place_tool
import os
from dotenv import load_dotenv
load_dotenv()
from crewai_tools import SerperDevTool
import time
agent_start_time = time.time()
search_tool = SerperDevTool()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY= os.getenv("SERPER_API_KEY")

# LLM 초기화
my_llm = LLM(
    model="gpt-4o-mini",
    api_key=OPENAI_API_KEY,
    temperature=0,
    max_tokens=4000
)

user_input = {
    "location": "인천",   # 사용자의 지역
    "age" : "40대",
    "concepts": "조용한, 디저트",  # 취향
    "parking": True,     # 주차 가능 여부
    "pet_friendly": True # 반려동물 동반 가능 여부
}

# 에이전트 정의
researcher = Agent(
    role="카페 정보 검색 및 분석 전문가",
    goal="고객 선호도에 맞는 최적의 카페 정보 수집 후 각 카페의 주요 특징, 시그니처 메뉴, 분위기 등 핵심 정보를 리뷰 및 사진에서 추출",
    backstory="사용자의 여행을 특별하게 만들기 위해, 최적의 카페를 찾고 카페의 매력을 심층 분석하여 사용자가 최적의 선택을 할 수 있도록 돕는 전문가",
    tools=[naver_place_tool],
    max_iter=2,
    llm=my_llm
)

ranker = Agent(
    role="카페 평가 및 순위 결정 전문가",
    goal="분석된 데이터를 기반으로 사용자 취향에 맞는 카페 3곳 선정",
    backstory="사용자 입력을 기반으로 가장 적합한 카페를 정밀하게 선정하는 평가 전문가.",
    max_iter=2,
    llm=my_llm
)

# (B) description에서 {location}, {parking}, {pet_friendly} 등 '개별 변수'만 사용
research_task = Task(
    description="""
    사용자 요청 지역({location})의 카페 정보를 검색하여 반환하세요.
    필수 조건:
    - 주차 가능 여부: {parking}
    - 애견 동반 가능 여부: {pet_friendly}
    - 검색 실패 시 "error" 메시지를 반환해야 합니다.
    """,
    expected_output="""
    카페 목록을 JSON 형태로 반환
    cafe_info = {
        "cafe_name" : "카페 이름",
        "info": {
            "address": "카페 주소",
            "business_time": "운영 시간",
            "tel_number": "전화 번호",
            "home_url": "홈페이지 주소",
            "img_url": "대표 이미지",
        },
        "reviews": "최신 리뷰 10개 리스트",
        "images" : "이미지 10개 url 리스트",
        "pet_friendly" : "애견 동반 가능 여부(bool)",
        "parking" : "주차 가능 여부(bool)",
        "signiture_menu" : "해당 카페에서 사람들이 찾는 시그니처 메뉴",
        "atmosphere" : "해당 카페의 분위기",
        "characteristic" : "해당 카페를 나타낼 수 있는 주요 키워드 5가지" 
    }
    """,
    agent=researcher,
    tools=[naver_place_tool],
)

ranker_task = Task(
    description="""
    다음 여행 정보를 분석하고, 고객의 선호도와 제약 사항을 파악하세요.
    - location: {location}
    - age: {age}
    - concepts: {concepts}
    - parking: {parking}
    - pet_friendly: {pet_friendly}

    1. researcher가 제공한 데이터를 기반으로 사용자에게 맞는 카페 3곳을 선정.
    2. 각 카페가 선택된 이유와 함께 cafe_info 반환.
    """,
    expected_output="""
    선정 이유와 함께 순위가 매겨진 3개의 카페의 cafe_info를 반환
        카페 목록을 JSON 형태로 반환
    cafe_info = {
        "cafe_name" : "카페 이름",
        "info": {
            "address": "카페 주소",
            "business_time": "운영 시간",
            "tel_number": "전화 번호",
            "home_url": "홈페이지 주소",
            "img_url": "대표 이미지",
        },
        "pet_friendly" : "애견 동반 가능 여부(bool)",
        "parking" : "주차 가능 여부(bool)",
        "signiture_menu" : "해당 카페에서 사람들이 찾는 시그니처 메뉴",
        "atmosphere" : "해당 카페의 분위기",
        "characteristic" : "해당 카페를 나타낼 수 있는 주요 키워드 5가지",
        "reason":"선택한 이유" 
    }
    """,
    agent=ranker,
)

crew = Crew(
    agents=[researcher, ranker],
    tasks=[research_task, ranker_task],
    process=Process.sequential,
    verbose=True,
)

try:
    result = crew.kickoff(inputs=user_input)
    print(result)
    agent_end_time = time.time()  # 🔴 종료 시간 기록
    agent_elapsed_time = agent_end_time - agent_start_time  # ⏳ 총 실행 시간 계산
    print(f"\n⏰ 실행 시간: {agent_elapsed_time:.2f} 초")  # 🚀 실행 시간 출력
except Exception as e:
    print(f"Error during execution: {e}")
