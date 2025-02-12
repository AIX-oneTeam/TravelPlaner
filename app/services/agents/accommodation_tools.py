from crewai.tools import BaseTool 
from serpapi import GoogleSearch
from geopy.geocoders import Nominatim
import json
import http.client
from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SERP_API_KEY = os.getenv("SERP_API_KEY")
    
# 위도,경도 계산 툴
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
    
    def _run(self, location: str, start_date: str, end_date:str,adults: int, children: int) -> str:
        try:            
            
            params = {
                "engine": "google_hotels",
                'q': f"{location} 숙소", 
                "check_in_date": start_date,
                "check_out_date": end_date,
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