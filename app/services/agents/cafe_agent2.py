# 홍대 카페를 추천해줌...

from crewai import Agent, Task, Crew, LLM, Process
from crewai_tools import SerperDevTool, ScrapeWebsiteTool, WebsiteSearchTool
from naver_place_tool import naver_place_tool
import os
from dotenv import load_dotenv
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# LLM 초기화
my_llm = LLM(
    model="gpt-4o-mini",
    api_key=OPENAI_API_KEY,
    temperature=0,
    max_tokens=4000
)

user_input = {
    "location":"인천",  # 사용자의 지역
    "age" : "40대",
    "companions" : {"adults": 2, "baby": 1},  # 동행인 세부사항
    "concepts":["조용한 분위기", "디저트가 맛있는 곳"],  # 취향
    "parking":True,  # 주차 가능 여부
    "pet_friendly":True  # 반려동물 동반 가능 여부
}

""" 에이전트 정의
- role : 핵심 역할
- goal : 최종적으로 달성해야 할 목표(장기적)
- backstory : 어떻게 행동해야 하는지에 대한 맥락, 행동 철학
- task : 수행해야 할 구체적인 작업(단기적)   
"""
# 에이전트 정의

researcher = Agent(
    role="카페 정보 검색 및 분석 전문가",
    goal="고객 선호도에 맞는 최적의 카페 정보 수집 후 각 카페의 주요 특징, 시그니처 메뉴, 분위기 등 핵심 정보를 리뷰 및 사진에서 추출 ",
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

# 태스크 정의
research_task = Task(
    description="""
    고객의 여행 선호도와 제약 사항에 대한 정보를 바탕으로 카페 정보 수집 후, 최신 리뷰와 이미지를 바탕으로 카페의 특징, 시그니처메뉴, 분위기 추출하여 정보 추가
    1. 조사한 카페의 리뷰와 이미지를 분석
    2. 리뷰 분석을 통해 공통적으로 칭찬받는 특징 3가지 추가.
    3. 사람들이 가장 많이 언급한 시그니처 메뉴 3가지 추가.
    4. 사진 데이터를 분석하여 카페의 주요 분위기 요소 3가지 추가.
    5. 각 카페에 대한 분석 결과를 간결하게 요약.
    """,
    expected_output="""
        각 카페의 주요 특징: 3가지 주요 강점, 3가지 시그니처 메뉴, 3가지 분위기 특징을 자료 조사한 결과에 추가
    """,
    agent=researcher,
    tools=[naver_place_tool],
    inputs={
        "query": f"{user_input['location']} 카페",
        "pet_friendly": user_input['pet_friendly'],
        "parking": user_input['parking']
    }
)

ranker_task = Task(
    description=f"""
    다음 여행 정보를 분석하고, 고객의 선호도와 제약 사항을 파악하세요.
    - location: {user_input['location']}
    - age : {user_input['age']}
    - companions : 성인 {user_input['companions']["adults"]}명, 아기{user_input['companions']["baby"]}명
    - concepts: {", ".join(user_input['concepts'])}
    - parking : {user_input['parking']}
    - pet_friendly : {user_input['pet_friendly']}

    1. analyst가 제공한 데이터를 기반으로 사용자의 상황에 맞게 순위를 매김.
    2. 우선순위 조건(예: 분위기, 주차 가능 여부, 메뉴)을 반영해 카페 3곳 선정.
    3. 각 카페가 선택된 이유를 간단히 설명하여 반환.
    """,
    expected_output="""
        선정 이유와 함께 순위가 매겨진 3개의 카페 정보를 반환
    """,
    agent=ranker,
    inputs={"analyzed_data": research_task.output}
)


# 멀티 에이전트 시스템 설정
crew = Crew(
    agents=[researcher, ranker],
    tasks=[research_task, ranker_task],
    process=Process.sequential,
    verbose=True,
)

# 실행
try:
    result = crew.kickoff(inputs=user_input)
    print(result)
except Exception as e:
    print(f"Error during execution: {e}")