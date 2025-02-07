import requests
from crewai import Agent, Crew, Process, Task
from crewai.project import agent, task, CrewBase, crew
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI 
from crewai.tools import BaseTool 
from urllib.parse import quote
from serpapi import GoogleSearch
from geopy.geocoders import Nominatim
from typing import List, Optional
import json
import http.client


load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SERP_API_KEY = os.getenv("SERP_API_KEY")


llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7, openai_api_key=OPENAI_API_KEY)

# AccommodationResponse 모델 정의
class AccommodationResponse(BaseModel):
    kor_name: str
    eng_name: Optional[str] = None
    description: str
    address: str
    latitude : str 
    longitude : str
    url: Optional[str] = None
    image_url: str
    map_url: str
    spot_category: int = 0
    phone_number: Optional[str] = None
    business_status: Optional[bool] = None
    business_hours: Optional[str] = None
    keywords: List[str]

    class Config:
        frozen = True
    
    
# 위도와 경도를 계산하는 툴
class GeoCoordinateTool(BaseTool):
    name: str = "GeoCoordinate Tool"
    description: str = "지역의 위도 경도를 계산"
    
    def _run(self, location: str) -> str:
        try:
            geo_local = Nominatim(user_agent='South Korea')
            geo = geo_local.geocode(location)
            if geo:
                location_coordinates = [geo.latitude, geo.longitude]
                return location_coordinates
        except Exception as e:
            return f"[GeoCoordinateTool] 에러: {str(e)}"      

# 구글 맵 툴 
class GoogleMapTool(BaseTool):
    name: str = "GoogleMapTool"
    description: str = "구글 맵 api를 사용하여 숙소 리스트 검색 툴"
    
    def _run(self, location: str, location_coordinates:str) -> str:
        try:
            conn = http.client.HTTPSConnection("google.serper.dev")

            payload = json.dumps({
            "q": f"{location}숙소",
            'll': f"@{location_coordinates},15.1z", 
            "gl": "kr",
            "hl": "ko"
            })
            headers = {
            'X-API-KEY': SERP_API_KEY,
            'Content-Type': 'application/json'
            }
            conn.request("POST", "/maps", payload, headers)
            res = conn.getresponse()
            data = res.read()
            print(data.decode("utf-8"))
            return json.loads(data.decode("utf-8"))
        except Exception as e:
            return f"[GoogleMapTool] 에러: {str(e)}"

# 구글 리뷰 툴 
class GoogleReviewTool(BaseTool):
    name: str = "GoogleReviewTool"
    description: str = "구글 리뷰 API를 이용, 리뷰 검색 툴 "
    
    def _run(self, cid: str, fid: str) -> str:
        try:            
            conn = http.client.HTTPSConnection("google.serper.dev")

            payload = json.dumps({
            "cid": cid,
            "fid": fid,
            "gl": "kr",
            "hl": "ko"
            })
            headers = {
            'X-API-KEY': SERP_API_KEY,
            'Content-Type': 'application/json'
            }
            conn.request("POST", "/reviews", payload, headers)
            res = conn.getresponse()
            data = res.read()
            print(data.decode("utf-8"))
            return json.loads(data.decode("utf-8"))
            
        except Exception as e:
            return f"[GoogleReviewTool] 에러: {str(e)}"
        
# 구글 호텔 툴
class GoogleHotelSearchTool(BaseTool):
    name: str = "Google Hotel Search"
    description: str = "구글 호텔 검색 API를 사용하여 텍스트 정보를 검색"
    
    def _run(self, location: str, check_in_date: str, check_out_date: str, adults: int, children: int) -> str:
        try:            
            
            params = {
                "engine": "google_hotels",
                'q': f"{location} 숙소", 
                "check_in_date": check_in_date,
                "check_out_date": check_out_date,
                "adults": adults,
                "children": children,
                "currency": "KRW",
                "gl": "kr",
                "hl": "ko",
                "api_key": GOOGLE_API_KEY
            }
            
            search = GoogleSearch(params)
            hotel_results = search.get_dict()
            print(f"전체 HOTEL API 응답: {hotel_results}")
            return hotel_results
        
        except Exception as e:
            return f"[GoogleHotelSearchTool] 에러: {str(e)}"        

@CrewBase
class AiLatestDevelopment():

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def accommodation_recommendation_expert(self) -> Agent:
        return Agent(
            config=self.agents_config['accommodation_recommendation_expert'],
            verbose=True,
            tools=[ GeoCoordinateTool(), GoogleMapTool(), GoogleReviewTool(),GoogleHotelSearchTool()],
            manager_llm=llm 
        )

    @task
    def accommodation_recommendation_task(self) -> Task:
        return Task(
            config=self.tasks_config['accommodation_recommendation_task'],
            output_pydantic=AccommodationResponse
        )
        
    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.accommodation_recommendation_expert()],
            tasks=[self.accommodation_recommendation_task()],
            process=Process.sequential,
            verbose=True
        )
        

# run 함수: 입력을 받아서 에이전트를 실행하고 결과 반환
def run(location: str, check_in_date: str, check_out_date: str, 
        age_group: int, adults: int, children: int, keyword: list) -> list:

    ai_dev = AiLatestDevelopment()
    crew_instance = ai_dev.crew()
    
    inputs = {
        "location": location,
        "check_in_date": check_in_date,
        "check_out_date": check_out_date,
        "age_group": age_group,
        "adults": adults,
        "children": children,
        "keyword": keyword
    }
    
    crew_output = crew_instance.kickoff(inputs=inputs)
    print(type(crew_output))

    if 'raw' in crew_output.__dict__:
        print(crew_output.__dict__['raw'])
        return crew_output.__dict__['raw']
    else:
        return {"error": "예상치 못한 출력 형식"}