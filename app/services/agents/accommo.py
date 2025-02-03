import requests
from crewai import Agent, Crew, Process, Task
from crewai.project import agent,task, CrewBase, crew
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI 
from crewai.tools import BaseTool 
from urllib.parse import quote
from serpapi import GoogleSearch


load_dotenv()
GOOGLE_API_KEY = 'MY-KEY'

os.environ["OPENAI_API_KEY"] = "MY-KEY"  
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)

class UserInput(BaseModel):
    start_date: str
    end_date: str
    region: str


class GoogleMapSearchTool(BaseTool):
    name: str = "Google Maps Search"
    description: str = "구글 맵 검색 API를 사용하여 텍스트 정보를 검색"
    
    def _run(self, location: str) -> str:  # location을 매개변수로 받도록 수정
        try:            
            # 위도 경도는 기본값으로 설정하되, 실제 검색 지역을 쿼리 파라미터로 사용
            location_coordinates = "@37.5665,126.9780,15.1z" 
            decoded_location = location.encode('utf-8').decode('unicode_escape')
            
            # 검색할 지역 이름을 'q' 파라미터에 넣기
            params = {
                'engine': 'google_maps',
                'q': f"{decoded_location} 숙소",  # 입력 받은 location 사용
                'll': location_coordinates,  
                "type": "search",
                "gl": "kr",
                "hl": "ko",
                'api_key': GOOGLE_API_KEY 
            }
            
            search = GoogleSearch(params)
            map_results = search.get_dict()
            results = map_results["local_results"]
            print(f"전체 API 응답: {map_results}")
            return results
        
        except Exception as e:
            return f"[Tool] 에러: {str(e)}"


@CrewBase
class AiLatestDevelopment():

    agents_config = "config/agents.yaml" 
    tasks_config = "config/tasks.yaml"

    @agent
    def accommodation_recommendation_expert(self) -> Agent:
        return Agent(
            config= self.agents_config['accommodation_recommendation_expert'],
            verbose=True,
            tools=[GoogleMapSearchTool()],
            manager_llm=llm # region을 전달
        )

    @task
    def accommodation_recommendation_task(self) -> Task:
        return Task(
            config=self.tasks_config['accommodation_recommendation_task']
        )
        
    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.accommodation_recommendation_expert()],
            tasks=[self.accommodation_recommendation_task()],
            process=Process.sequential,
            verbose=True
        )

def run():
    ai_dev = AiLatestDevelopment()  # 인스턴스 생성
    crew_instance = ai_dev.crew()  # Crew 객체 획득
    r = crew_instance.kickoff(inputs={"location": "서울"})     # 실행
    print(r)

run()