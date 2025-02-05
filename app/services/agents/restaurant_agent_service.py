import traceback
import os
import requests
import json
from fastapi import FastAPI, HTTPException
from crewai import Agent, Task, Crew, LLM
from datetime import datetime, timedelta
from dotenv import load_dotenv
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from sqlalchemy import Column, Double
from typing import List, Dict
import aiohttp
import asyncio

app = FastAPI()

# 환경 변수 로드
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
GOOGLE_MAP_API_KEY = os.getenv("GOOGLE_MAP_API_KEY")
AGENT_NAVER_CLIENT_ID = os.getenv("AGENT_NAVER_CLIENT_ID")
AGENT_NAVER_CLIENT_SECRET = os.getenv("AGENT_NAVER_CLIENT_SECRET")

llm = LLM(model="gpt-3.5-turbo", temperature=0, api_key=OPENAI_API_KEY)


# 모델 정의
class Companion(BaseModel):
    label: str
    count: int


class TravelPlan(BaseModel):
    main_location: str
    start_date: str
    end_date: str
    companions: List[Companion]
    concepts: List[str]


class spot_pydantic(BaseModel):
    kor_name: str = Field(max_length=255)
    eng_name: str = Field(default=None, max_length=255)
    description: str = Field(max_length=255)
    address: str = Field(max_length=255)
    url: str = Field(default=None, max_length=2083)
    image_url: str = Field(max_length=2083)
    map_url: str = Field(max_length=2083)
    latitude: float = Field(sa_column=Column(Double, nullable=False))
    longitude: float = Field(sa_column=Column(Double, nullable=False))
    spot_category: int
    phone_number: str = Field(default=None, max_length=300)
    business_status: bool = None
    business_hours: str = Field(default=None, max_length=255)
    order: int
    day_x: int
    spot_time: str = None


class spots_pydantic(BaseModel):
    spots: List[spot_pydantic]


# Google Geocoding API 활용한 좌표 조회 도구
class GeocodingTool(BaseTool):
    name: str = "GeocodingTool"
    description: str = (
        "Google Geocoding API를 사용하여 주어진 위치의 위도와 경도를 조회합니다. "
        "입력된 location 값은 변경 없이 그대로 반환합니다."
    )

    def _run(self, location: str) -> Dict:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": location, "key": GOOGLE_MAP_API_KEY}
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("results"):
                loc = data["results"][0]["geometry"]["location"]
                coordinates = f"{loc['lat']},{loc['lng']}"
            else:
                coordinates = ""
        except Exception as e:
            coordinates = f"[GeocodingTool] Error: {str(e)}"
        return {"location": location, "coordinates": coordinates}


# 맛집 기본 정보 조회 도구
class RestaurantBasicSearchTool(BaseTool):
    name: str = "RestaurantBasicSearchTool"
    description: str = (
        "주어진 좌표와 location 정보를 기반으로 구글맵에서 식당의 title, rating, reviews를 검색합니다."
    )

    def get_place_details(self, place_id: str) -> Dict:
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "fields": "name,rating,user_ratings_total,geometry",
            "language": "ko",
            "key": GOOGLE_MAP_API_KEY,
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            result = data.get("result", {})

            return {
                "title": result.get("name"),
                "rating": result.get("rating", 0),
                "reviews": result.get("user_ratings_total", 0),
                "latitude": result["geometry"]["location"]["lat"],
                "longitude": result["geometry"]["location"]["lng"],
            }
        except Exception as e:
            print(f"[RestaurantBasicSearchTool] Details Error: {e}")
            return None

    def _run(self, location: str, coordinates: str) -> List[Dict]:
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        all_candidates = []

        lat, lng = coordinates.split(",")

        # 첫 20개 요청
        params = {
            "query": f"{location} 맛집",
            "language": "ko",
            "type": "restaurant",
            "key": GOOGLE_MAP_API_KEY,
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            for place in data.get("results", []):
                place_id = place.get("place_id")
                if place_id:
                    details = self.get_place_details(place_id)
                    if details:
                        all_candidates.append(details)

            # 추가 20개 요청
            if data.get("next_page_token"):
                time.sleep(2)
                params["pagetoken"] = data["next_page_token"]
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                for place in data.get("results", []):
                    if len(all_candidates) >= 40:
                        break
                    place_id = place.get("place_id")
                    if place_id:
                        details = self.get_place_details(place_id)
                        if details:
                            all_candidates.append(details)

        except Exception as e:
            print(f"[RestaurantBasicSearchTool] Search Error: {e}")

        return all_candidates


# 맛집 필터링 도구 - 기존과 동일
class RestaurantFilterTool(BaseTool):
    name: str = "RestaurantFilterTool"
    description: str = (
        "조회된 맛집 리스트 중 평점 4.0 이상, 리뷰 500개 이상인 식당만 필터링합니다."
    )

    def _run(self, candidates: List[Dict]) -> List[Dict]:
        return [
            r
            for r in candidates
            if r.get("rating", 0) >= 4.0 and r.get("reviews", 0) >= 500
        ]


class NaverWebSearchTool(BaseTool):
    name: str = "NaverWebSearch"
    description: str = (
        "네이버 웹 검색 API를 사용해 식당의 텍스트 기반 세부 정보를 검색합니다."
    )

    def fetch(self, query: str):
        url = "https://openapi.naver.com/v1/search/webkr.json"
        headers = {
            "X-Naver-Client-Id": AGENT_NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": AGENT_NAVER_CLIENT_SECRET,
        }
        params = {"query": query, "display": 1, "start": 1, "sort": "random"}

        try:
            response = requests.get(url, headers=headers, params=params)
            data = response.json()
            items = data.get("items", [])
            if not items:
                return {"description": "정보 없음", "url": ""}
            return {
                "description": items[0].get("description", "정보 없음"),
                "url": items[0].get("link", ""),
            }
        except Exception as e:
            return {"description": f"에러 발생: {str(e)}", "url": ""}

    def _run(self, restaurant_list: List[str]) -> Dict[str, Dict[str, str]]:
        results = {}
        for restaurant in restaurant_list:
            results[restaurant] = self.fetch(restaurant)
        return results


class NaverImageSearchTool(BaseTool):
    name: str = "NaverImageSearch"
    description: str = "네이버 이미지 검색 API를 사용해 식당의 이미지 URL을 검색합니다."

    def fetch(self, query: str):
        url = "https://openapi.naver.com/v1/search/image"
        headers = {
            "X-Naver-Client-Id": AGENT_NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": AGENT_NAVER_CLIENT_SECRET,
        }
        params = {"query": query, "display": 1, "sort": "sim"}

        try:
            response = requests.get(url, headers=headers, params=params)
            data = response.json()
            items = data.get("items", [])
            if not items:
                return ""
            return items[0].get("link", "")
        except Exception as e:
            return f"에러 발생: {str(e)}"

    def _run(self, restaurant_list: List[str]) -> Dict[str, str]:
        results = {}
        for restaurant in restaurant_list:
            results[restaurant] = self.fetch(restaurant)
        return results


class FinalRecommendationTool(BaseTool):
    name: str = "FinalRecommendationTool"
    description: str = (
        "필터링된 맛집 후보와 상세 정보를 결합하여 최종 추천 리스트를 생성합니다."
    )

    def _run(self, inputs: Dict) -> Dict:
        filtered_list = inputs.get("filtered_list", [])
        text_details = inputs.get("text_details", {})
        image_urls = inputs.get("image_urls", {})
        travel_plan = inputs.get("travel_plan", {})

        start_date = datetime.strptime(travel_plan.get("start_date"), "%Y-%m-%d")
        end_date = datetime.strptime(travel_plan.get("end_date"), "%Y-%m-%d")
        total_days = (end_date - start_date).days + 1

        spots = []
        day_x = 1
        order = 1

        for restaurant in filtered_list:
            name = restaurant["title"]
            details = text_details.get(name, {})

            spot_time = (
                "08:00 AM" if order == 1 else "12:00 PM" if order == 2 else "07:00 PM"
            )

            spot = spot_pydantic(
                kor_name=name,
                eng_name=details.get("eng_name"),
                description=details.get("description", "정보 없음"),
                address=details.get("address", "주소 없음"),
                latitude=restaurant["latitude"],
                longitude=restaurant["longitude"],
                url=details.get("url"),
                image_url=image_urls.get(name, ""),
                map_url=f"https://maps.google.com/?q={restaurant['latitude']},{restaurant['longitude']}",
                spot_category=2,
                phone_number=details.get("phone_number"),
                business_status=details.get("business_status", True),
                business_hours=details.get("business_hours"),
                order=order,
                day_x=day_x,
                spot_time=spot_time,
            )
            spots.append(spot)

            if order == 3:
                order = 1
                day_x += 1
                if day_x > total_days:
                    break
            else:
                order += 1

        return {"spots": spots}


# ------------------------- Agent ------------------------------
# 좌표 조회 에이전트
geocoding_agent = Agent(
    role="좌표 조회 전문가",
    goal="사용자가 입력한 location(예: '부산광역시')의 위도와 경도를 조회하며, location 값은 그대로 유지한다.",
    backstory="나는 위치 데이터 전문가로, 입력된 location 값을 변경하지 않고 Google Geocoding API를 통해 좌표를 조회한다.",
    tools=[GeocodingTool()],
    llm=llm,
    verbose=True,
)

# 맛집 기본 조회 에이전트
restaurant_basic_search_agent = Agent(
    role="맛집 기본 조회 전문가",
    goal="좌표 정보를 활용하여 식당의 기본 정보(구글맵의 title, rating, reviews, 위도, 경도)를 조회한다.",
    backstory="나는 맛집 데이터 분석 전문가로, Google Maps API를 사용하여 특정 위치의 식당 정보를 최대 40개까지 조회한다.",
    tools=[RestaurantBasicSearchTool()],
    llm=llm,
    verbose=True,
)

# 맛집 필터링 에이전트
restaurant_filter_agent = Agent(
    role="맛집 필터링 전문가",
    goal="평점과 리뷰 수 기준으로 식당 후보를 선별한다.",
    backstory="나는 데이터 필터링 전문가로, 맛집 리뷰와 평점을 분석하여 신뢰할 수 있는 식당 후보를 추려낸다.",
    tools=[RestaurantFilterTool()],
    llm=llm,
    verbose=True,
)

# 네이버 웹 검색 에이전트
naver_web_search_agent = Agent(
    role="네이버 웹 검색 에이전트",
    goal="네이버 웹 검색 API를 사용해 식당의 텍스트 기반 세부 정보를 조회한다.",
    backstory="네이버 웹 검색을 통해 식당의 상세 텍스트 정보를 제공합니다.",
    tools=[NaverWebSearchTool()],
    llm=llm,
    verbose=True,
)

# 네이버 이미지 검색 에이전트
naver_image_search_agent = Agent(
    role="네이버 이미지 검색 에이전트",
    goal="네이버 이미지 검색 API를 사용해 식당의 이미지 URL을 조회한다.",
    backstory="네이버 이미지 검색을 통해 식당의 이미지를 제공합니다.",
    tools=[NaverImageSearchTool()],
    llm=llm,
    verbose=True,
)

# 최종 추천 생성 에이전트
final_recommendation_agent = Agent(
    role="최종 추천 에이전트",
    goal="수집된 모든 정보를 종합하여 최종 맛집 추천 리스트를 생성한다.",
    backstory="나는 데이터 구조화 전문가로, 모든 수집 정보를 종합하여 여행 일정에 맞는 맛집 추천 리스트를 구성한다.",
    tools=[FinalRecommendationTool()],
    llm=llm,
    verbose=True,
    output_pydantic=spots_pydantic,
)


# ------------------------- Task & Crew ------------------------------
def create_recommendation(input_data: dict) -> dict:
    try:
        travel_plan = TravelPlan(**input_data)

        # Task 정의
        tasks = [
            Task(
                description=f"{travel_plan.main_location}의 좌표 조회",
                agent=geocoding_agent,
                expected_output="{'location': '부산광역시', 'coordinates': '35.1796,129.0756'}",
                tools=[GeocodingTool()],
                config={},  # 빈 딕셔너리로 config 추가
            ),
            Task(
                description="맛집 기본 정보 조회",
                agent=restaurant_basic_search_agent,
                expected_output="리스트 형태로 title, rating, reviews, latitude, longitude 정보를 포함한 맛집 리스트",
                tools=[RestaurantBasicSearchTool()],
                config={},
            ),
            Task(
                description="맛집 필터링",
                agent=restaurant_filter_agent,
                expected_output="평점 4.0 이상, 리뷰 500개 이상인 맛집 리스트",
                tools=[RestaurantFilterTool()],
                config={},
            ),
            Task(
                description="맛집 세부 정보 조회",
                agent=naver_web_search_agent,
                expected_output="각 식당의 네이버 웹 검색 결과에서 세부 정보 (주소, 설명, 전화번호 등) 포함",
                tools=[NaverWebSearchTool()],
                config={},
            ),
            Task(
                description="맛집 이미지 조회",
                agent=naver_image_search_agent,
                expected_output="각 식당의 대표 이미지 URL",
                tools=[NaverImageSearchTool()],
                config={},
            ),
            Task(
                description="최종 추천 리스트 생성",
                agent=final_recommendation_agent,
                expected_output="spot_pydantic 구조를 따르는 최종 추천 리스트",
                tools=[FinalRecommendationTool()],
                config={
                    "travel_plan": travel_plan.dict(),
                    "previous_results": "이전 태스크들의 결과물을 활용",
                },
            ),
        ]

        crew = Crew(
            tasks=tasks,
            agents=[
                geocoding_agent,
                restaurant_basic_search_agent,
                restaurant_filter_agent,
                naver_web_search_agent,
                naver_image_search_agent,
                final_recommendation_agent
            ],
            verbose=True
        )

        result = crew.kickoff()
        return result

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# FastAPI 엔드포인트
@app.post("/restaurant")
async def get_restaurant_recommendations(travel_plan: TravelPlan):
    try:
        result = create_recommendation(travel_plan.dict())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 서버 실행 설정
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
