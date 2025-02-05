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
from geopy.geocoders import Nominatim
from typing import List, Dict
import json


load_dotenv()
OPENAI_API_KEY = "key"
GOOGLE_API_KEY = "key"
 
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7, openai_api_key=OPENAI_API_KEY)

class UserInput(BaseModel):
    start_date: str
    end_date: str
    region: str

#위도 경도 툴
class GeoCoordinateTool(BaseTool):
    name: str = "GeoCoordinate Tool"
    description:str = " 지역의 위도 경도를 계산"
    
    def _run(self, location : str) -> str:
        try:
            geo_local = Nominatim(user_agent='South Korea')
            geo = geo_local.geocode(location)
            if geo:
                x_y = [geo.latitude, geo.longitude]
                return x_y
            
        except Exception as e:
            return f"[GeoCoordinateTool] 에러: {str(e)}"

#구글 맵 툴
class GoogleMapSearchTool(BaseTool):
    name: str = "Google Maps Search"
    description: str = "구글 맵 검색 API를 사용하여 텍스트 정보를 검색"
    
    def _run(self, location: str, location_coordinates:str ) -> str: 
        try:            
            decoded_location = location.encode('utf-8').decode('unicode_escape')
            
            params = {
                'engine': 'google_maps',
                'q': f"{decoded_location} 숙소", 
                'll': f"@{location_coordinates},15.1z",  
                "type": "search",
                "gl": "kr",
                "hl": "ko",
                'api_key': GOOGLE_API_KEY 
            }
            
            search = GoogleSearch(params)
            map_results = search.get_dict()
            print(f"전체 MAP API 응답: {map_results}")
            return map_results
        
        except Exception as e:
            return f"[GoogleMapSearchTool] 에러: {str(e)}"
        
#구글 호텔 툴
class GoogleHotelSearchTool(BaseTool):
    name: str = "Google Hotel Search"
    description: str = "구글 호텔 검색 API를 사용하여 텍스트 정보를 검색"
    
    def _run(self, location: str, check_in_date:str, check_out_date:str, adults:int, children:int) -> str: 
        try:            
            decoded_location = location.encode('utf-8').decode('unicode_escape')
            
            params = {
            "engine": "google_hotels",
            'q': f"{decoded_location} 숙소", 
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

#구글 리뷰 툴
class GoogleReviewTool(BaseTool) :
    name: str = "GoogleReviewTool"
    description: str = "구글 리뷰 API를 사용하여 텍스트 정보를 검색"
    
    def _run(self, data_id : str) -> str:
        try:
            params = {
            "engine": "google_maps_reviews",
            "data_id": data_id,
            "gl": "kr",
            "hl": "ko",
            "api_key": GOOGLE_API_KEY 
            }

            search = GoogleSearch(params)
            review_results = search.get_dict()
            print(f"전체 REVIEW API 응답: {review_results}")
            
            return review_results 
        
        except Exception as e:
            return f"[GoogleReviewTool] 에러: {str(e)}"   


@CrewBase
class AiLatestDevelopment():

    agents_config = "config/agents.yaml" 
    tasks_config = "config/tasks.yaml"

    @agent
    def accommodation_recommendation_expert(self) -> Agent:
        return Agent(
            config= self.agents_config['accommodation_recommendation_expert'],
            verbose=True,
            tools=[GeoCoordinateTool(), GoogleMapSearchTool(),GoogleHotelSearchTool(),GoogleReviewTool()],
            manager_llm=llm 
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
           
           
def run(location: str, check_in_date: str, check_out_date: str, 
        age_group: int, adults:int, children:int, keyword:list)->list:

    ai_dev = AiLatestDevelopment()
    crew_instance = ai_dev.crew()
    
    inputs = {
        "location": location,
        "check_in_date": check_in_date,
        "check_out_date": check_out_date,
        "age_group" : age_group,
        "adults" : adults,
        "children":children,
        "keyword": keyword
    }
    
    result = crew_instance.kickoff(inputs=inputs)
    return result