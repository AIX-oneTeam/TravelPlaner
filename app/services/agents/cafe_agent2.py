import os
from dotenv import load_dotenv
# 환경 변수 로드
load_dotenv(dotenv_path="../../../.env")
# OpenAI API 키 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
from crewai_tools import SerperDevTool, ScrapeWebsiteTool, WebsiteSearchTool
from crewai import Agent, Task, Crew, LLM, Process

search_tool = SerperDevTool() # 검색 엔진을 통해 웹 데이터를 가져오는 도구
scrape_tool = ScrapeWebsiteTool() # 특정 웹사이트에서 데이터를 스크래핑하는 도구
web_rag_tool = WebsiteSearchTool() # 특정 키워드나 주제에 대해 웹 검색을 수행하는 도구

result = search_tool.run(query="quiet cafes in Incheon")
result2 = scrape_tool.run(url="https://map.naver.com",query="quiet cafes in Incheon")
result3 = web_rag_tool.run(query="quiet cafes in Incheon")
print(result)  # 결과 확인
print(result2)  # 결과 확인
print(result)3  # 결과 확인

# LLM 초기화
my_llm = LLM(
    model="gpt-4o-mini",
    api_key=OPENAI_API_KEY,
    temperature=0,
    # max_tokens=4000
)

user_info = {
    "location":"인천",  # 사용자의 지역
    "age" : "40대",
    "companions" : {"pets": 1, "adults": 2, "teens": 1},  # 동행인 세부사항
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
    role="검색 전문가",
    goal="사용자 입력를 반영한 카페 후보 5~7곳 조사",
    backstory="사용자의 여행을 특별하게 만들기 위해, 최적의 카페 후보를 선별하는 검색 전문가.",
    tools=[search_tool, scrape_tool, web_rag_tool],
    llm=my_llm
)

analyst = Agent(
    role="카페 리뷰 및 분위기 분석 전문가",
    goal="각 카페의 주요 특징, 시그니처 메뉴, 분위기 등 핵심 정보를 리뷰 및 사진에서 추출",
    backstory="카페의 매력을 심층 분석하여 사용자가 최적의 선택을 할 수 있도록 돕는 전문가.",
    tools=[search_tool, scrape_tool, web_rag_tool],
    llm=my_llm
)

ranker = Agent(
    role="카페 평가 및 순위 결정 전문가",
    goal="분석된 데이터를 기반으로 사용자 취향에 맞는 카페 3곳 선정",
    backstory="사용자 입력을 기반으로 가장 적합한 카페를 정밀하게 선정하는 평가 전문가.",
    llm=my_llm
)

verifier = Agent(
    role="품질 및 정보 검증 전문가",
    goal="최종적으로 선정된 3개 카페의 폐업 여부와 기본 정보를 확인 및 보완",
    backstory="정확하고 신뢰할 수 있는 정보를 제공하기 위해 세부 정보를 검증하고 보완하는 전문가.",
    tools=[search_tool, scrape_tool, web_rag_tool],
    llm=my_llm
)

# 태스크 정의
research_task = Task(
    description=f"""
1. 사용자가 입력한 지역 ({user_info['location']})과 취향 ({", ".join(user_info['concepts'])})을 기반으로 카페를 검색합니다.
2. 신뢰할 수 있는 데이터 소스를 사용해 카페 후보를 조사합니다.
3. 요청된 조건에 부합하는 5~7곳의 카페를 선정하여 요약합니다.
""",
    expected_output="""
        5~7개의 카페 목록과 기본 정보(이름, 주소, 주요 특징)
    """,
    agent=researcher
)

analyst_task = Task(
    description="""
    1. researcher가 반환한 카페 목록의 리뷰와 사진 데이터를 수집.
    2. 리뷰 분석을 통해 공통적으로 칭찬받는 특징 3가지 추출.
    3. 사람들이 가장 많이 언급한 시그니처 메뉴 3가지 정리.
    4. 사진 데이터를 분석하여 카페의 주요 분위기 요소 3가지 추출.
    5. 각 카페에 대한 분석 결과를 간결하게 요약하여 반환.
    """,
    expected_output="""
        각 카페의 주요 특징: 3가지 주요 강점, 3가지 시그니처 메뉴, 3가지 분위기 특징
    """,
    agent=analyst
)

ranker_task = Task(
    description=f"""
    1. researcher가 제공한 데이터를 기반으로 사용자 취향({", ".join(user_info['concepts'])})에 따라 순위를 매김.
    2. 우선순위 조건(예: 분위기, 주차 가능 여부, 메뉴)을 반영해 카페 3곳 선정.
    3. 각 카페가 선택된 이유를 간단히 설명하여 반환.
    """,
    expected_output="""
        선정 이유와 함께 순위가 매겨진 3개의 카페 목록
    """,
    agent=ranker
)

verifier_task = Task(
    description="""
    1. ranker가 제공한 카페 목록의 폐업 여부를 확인.
    2. 폐업된 카페는 순위에서 제외하고 다음 순위의 카페를 대체.
    3. 최종 3개 카페의 정확한 정보를 정리:
       - 이름, 영문 이름, 주소, 운영시간, 지도 URL, 대표 이미지 URL
       - 주차 가능 여부, 반려동물 동반 가능 여부.
    """,
    expected_output="""
        3개의 카페에 대한 상세 정보: 이름, 주소, 운영 시간, URL, 주차 가능 여부, 반려동물 동반 가능 여부
    """,
    agent=verifier
)

# 멀티 에이전트 시스템 설정
crew = Crew(
    agents=[researcher, analyst, ranker, verifier],
    tasks=[research_task, analyst_task, ranker_task, verifier_task],
    process=Process.sequential,
    verbose=True,
)

# 실행
try:
    result = crew.kickoff(inputs=user_info)
    print(result)
except Exception as e:
    print(f"Error during execution: {e}")

