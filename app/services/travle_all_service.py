import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from langchain.tools import DuckDuckGoSearchRun
from langchain.agents import Tool

# 환경 변수 로드
load_dotenv()

# LLM 초기화
gpt = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0,
    max_tokens=4000
)

# DuckDuckGoSearchRun 초기화
search_tool = DuckDuckGoSearchRun()

# 검색 도구 래퍼 함수
def search_wrapper(query):
    if not isinstance(query, str):
        raise ValueError("Search query must be a string.")
    print(f"Performing search with query: {query}")
    return search_tool.run(query)

# 에이전트 생성 함수
def create_agent(role, goal, backstory, instructions):
    return Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        instructions=instructions,
        verbose=True,
        allow_delegation=False,
        tools=[
            Tool(
                name="Search",
                func=search_wrapper,
                description="유용한 정보를 검색하는 도구"
            )
        ],
        llm=gpt
    )

# 에이전트 정의
def create_agents():
    return {
        "schedule_agent": create_agent(
            role="여행 일정 전문가",
            goal="고객의 관심사와 일정에 맞는 최적의 서울 여행 일정 작성",
            backstory="10년 경력의 여행 플래너로, 서울의 관광지, 맛집, 카페에 대한 깊은 지식을 보유하고 있습니다.",
            instructions="""
            고객의 나이, 동행인 수, 여행 기간을 고려하여 서울 여행 일정을 작성하세요.
            각 날짜별로 방문할 장소를 다음 형식으로 제공하세요:
            - 시간: HH:MM
            - 순서: 방문 순서
            - 장소: 장소 이름
            - 장소 설명: 간단한 설명
            - 장소 주소: 정확한 주소
            - 사진 URL: 해당 장소의 사진 URL
            """
        )
    }

# Task 정의
def create_tasks(input_data):
    return [
        Task(
            description=f"{input_data['location']}의 최적화된 여행 일정 작성",
            agent=input_data["agents"]["schedule_agent"],
            input_data=input_data,
            expected_output="날짜별로 시간, 순서, 장소, 장소 설명, 장소 주소, 사진 URL이 포함된 여행 일정"
        )
    ]

# Crew 실행 함수
def execute_travel_plan(input_data):
    agents = create_agents()
    input_data["agents"] = agents  # 에이전트 정보 추가
    tasks = create_tasks(input_data)
    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential
    )

    # Crew 실행 및 결과 반환
    return crew.kickoff()

# 테스트 입력값
if __name__ == "__main__":
    input_data = {
        "location": "서울",
        "start_date": "2025-01-24",
        "end_date": "2025-01-26",
        "age": "20대",
        "companions": {
            "adults": 2,
            "teens": 1
        }
    }

    print("=== 여행 계획 생성 시작 ===")
    try:
        result = execute_travel_plan(input_data)
        print("\n=== 최종 여행 계획 ===")
        for day_plan in result:
            print(day_plan)
    except Exception as e:
        print("\n에러 발생:", e)
