# services/travel_agent_service.py
from crewai import Agent, Task, Crew, Process
from app.services.agents.travel_agent_service import (
    create_attraction_agent,
    create_food_cafe_agent,
    create_accommodation_agent,
    create_schedule_agent
)


async def create_travel_plan(location, start_date, end_date, age, companions):
    # 에이전트 생성
    attraction_agent = await create_attraction_agent()
    food_cafe_agent = await create_food_cafe_agent()
    accommodation_agent = await create_accommodation_agent()
    schedule_agent = await create_schedule_agent()
    
    # Task 정의
# Task 정의
    tasks = [

        Task(
            description=f"""
            {location}의 관광지 추천:
            - 날짜: {start_date} ~ {end_date}
            - 연령대: {age}
            - 동행인: {companions}
            """,
            agent=attraction_agent
    ),
        Task(
            description=f"{location}의 맛집과 카페 추천",
            agent=food_cafe_agent
    ),
        Task(
            description=f"{location}의 숙소 추천",
            agent=accommodation_agent
    ),
    Task(
        description=f"{location}의 최종 여행 일정 작성",
        agent=schedule_agent
    )
]


    # Crew 구성 및 실행
    crew = Crew(
        agents=[attraction_agent, food_cafe_agent, accommodation_agent],
        tasks=tasks,
        process=Process.sequential
    )

    return await crew.kickoff()
