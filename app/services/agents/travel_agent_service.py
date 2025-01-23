# services/agents/travel_agents.py
from crewai import LLM, Agent
from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

llm = LLM(
    model="gpt-4o-mini",  # 또는 원하는 모델
    temperature=0.7,
    api_key=OPENAI_API_KEY
)

async def create_attraction_agent():
    return Agent(
        role="관광지 전문가",
        goal="방문객 특성에 맞는 실제 존재하는 관광지 추천",
        backstory="한국의 실제 관광지를 전문적으로 조사하고 추천하는 전문가",
        verbose=True
    )

async def create_food_cafe_agent():
    return Agent(
        role="맛집/카페 전문가",
        goal="지역 특성에 맞는 실제 맛집과 카페 추천",
        backstory="한국의 실제 맛집과 카페를 전문적으로 조사하고 추천하는 전문가",
        verbose=True
    )

async def create_accommodation_agent():
    return Agent(
        role="숙소 전문가",
        goal="여행객 조건에 맞는 실제 최적의 숙소 추천",
        backstory="한국의 실제 숙소를 전문적으로 조사하고 추천하는 전문가",
        verbose=True
    )

async def create_schedule_agent():
    return Agent(
        role="일정 계획가",
        goal="추천된 장소들을 바탕으로 최적의 일정 및 동선 생성",
        backstory="방문 시간, 장소 위치, 이동 시간을 고려하여 최적의 여행 일정을 만드는 전문가",
        verbose=True
    )
