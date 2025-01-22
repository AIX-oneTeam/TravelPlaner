# services/travel_agent_service.py

from services.agents.accommodation_agent import create_accommodation_agent
from services.agents.attraction_agent import create_attraction_agent
from services.agents.food_cafe_agent import create_food_cafe_agent
from crewai import Task, Crew, Process

def create_travel_plan(location, date, age_group, companions):
    """
    location: str
    date: str
    age_group: str
    companions: str

    Returns: {
      "food_cafe": [...],
      "attraction": [...],
      "accommodation": [...]
    } 형태의 딕셔너리
    """

    # 1) 에이전트 생성
    food_cafe_agent = create_food_cafe_agent()
    attraction_agent = create_attraction_agent()
    accommodation_agent = create_accommodation_agent()

    # 2) 에이전트가 수행할 Task 정의
    #    - 에이전트에게 넘길 쿼리는 "location + 맛집/관광/숙소" 정도로 구성
    tasks = [
        Task(
            description=f"{location} 맛집/카페 검색", 
            agent=food_cafe_agent,
            # 아래 kwargs는 crewai가 내부적으로 tool을 호출할 때 쓸 인자(검색어)로 활용 가능
            kwargs={"query": f"{location} 맛집"}  
        ),
        Task(
            description=f"{location} 관광지 검색", 
            agent=attraction_agent,
            kwargs={"query": f"{location} 관광지"}
        ),
        Task(
            description=f"{location} 숙소 검색", 
            agent=accommodation_agent,
            kwargs={"query": f"{location} 숙소"}
        ),
    ]

    # 3) Crew 생성
    crew = Crew(
        agents=[food_cafe_agent, attraction_agent, accommodation_agent],
        tasks=tasks,
        process=Process.sequential  # 순차적으로 작업
    )

    # 4) 작업 실행
    result_data = crew.kickoff()
    # kickoff() 결과는 기본적으로 [ <food_cafe 결과>, <attraction 결과>, <accommodation 결과> ] 식으로
    # 순서대로 반환된다고 가정 (CrewAI 버전에 따라 다를 수 있음)

    # 5) 카테고리별로 묶어서 최종 결과 딕셔너리로 만들어 보겠습니다.
    #    (만약 kickoff 결과 구조가 다르다면, 그에 맞춰 조정 필요)
    # result_data[0] => 맛집/카페 목록
    # result_data[1] => 관광지 목록
    # result_data[2] => 숙소 목록
    return {
        "food_cafe": result_data[0],
        "attraction": result_data[1],
        "accommodation": result_data[2]
    }
