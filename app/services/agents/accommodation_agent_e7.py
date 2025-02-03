from pydantic import BaseModel
from crewai import Agent, Crew, Process
from crewai.project import CrewBase, agent
from crewai_tools import SerperDevTool
import yaml
from dotenv import load_dotenv
import os

# 구글 맵 API 클라이언트 설정
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

llm = LLM(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY)


# 사용자 입력 데이터 모델 정의
class UserInput(BaseModel):
    start_date: str
    end_date: str
    region: str
    

# map 툴 정의 
def accommo_map_search(region: str, start_date: str, end_date: str) -> str:
    """주어진 지역과 날짜에 맞는 숙소를 추천하는 도구."""
    
    places_result = gmaps.places(query=f"hotel in {region}")

    # 결과에서 숙소 이름을 추출
    hotels = []
    for place in places_result.get('results', []):
        hotel_name = place.get('name')
        hotels.append(hotel_name)

    if hotels:
        return f"{region}에서 {start_date}부터 {end_date}까지 이용 가능한 숙소: " + ", ".join(hotels)
    else:
        return f"{region}에서 {start_date}부터 {end_date}까지 숙소를 찾을 수 없습니다."
    
# hotel 툴 정의     

# YAML 파일에서 에이전트 설정을 불러오는 함수
def load_agents_config():
    with open("config/agents.yaml", "r", encoding="utf-8") as file:
        return yaml.safe_load(file)

# CrewBase 정의
@CrewBase
class AccommodationCrew:
    """숙소 추천 크루"""

    agents_config = load_agents_config()

    @agent
    def accommo_researcher(self) -> Agent:
        return Agent(
            role=self.agents_config['accommo_researcher']['role'],
            goal=self.agents_config['accommo_researcher']['goal'],
            backstory=self.agents_config['accommo_researcher']['backstory'],
            tools=[recommend_accommodation],
            verbose=True,
        )

# 사용자 입력 예시
user_input = UserInput(start_date="2025-05-01", end_date="2025-05-07", region="Seoul")

# 크루 및 에이전트 실행 예시
crew = AccommodationCrew()

# 에이전트를 호출하여 숙소 추천 실행
result = crew.accommo_researcher.run(region=user_input.region, start_date=user_input.start_date, end_date=user_input.end_date)
print(result)  # 예: 서울에서 2025-05-01부터 2025-05-07까지 이용 가능한 숙소: 호텔 A, 호텔 B, 호텔 C
