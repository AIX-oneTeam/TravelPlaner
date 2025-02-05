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
from typing import List, Dict

app = FastAPI()

# 환경 변수 로드
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
GOOGLE_MAP_API_KEY = os.getenv("GOOGLE_MAP_API_KEY")
AGENT_NAVER_CLIENT_ID = os.getenv("AGENT_NAVER_CLIENT_ID")
AGENT_NAVER_CLIENT_SECRET = os.getenv("AGENT_NAVER_CLIENT_SECRET")

llm = LLM(model="gpt-3.5-turbo", temperature=0, api_key=OPENAI_API_KEY)


# 사용자 여행 데이터 입력 스키마
class Companion(BaseModel):
    label: str
    count: int


class TravelPlan(BaseModel):
    main_location: str
    start_date: str
    end_date: str
    companions: List[Companion]
    concepts: List[str]


class RestaurantSearchArgs(BaseModel):
    location: str
    coordinates: str


class spot_pydantic(BaseModel):
    kor_name: str = Field(max_length=255)
    eng_name: str = Field(default=None, max_length=255)
    description: str = Field(max_length=255)
    address: str = Field(max_length=255)
    latitude: str = Field(max_length=100)
    longitude: str = Field(max_length=100)
    url: str = Field(default=None, max_length=2083)
    image_url: str = Field(max_length=2083)
    map_url: str = Field(max_length=2083)
    spot_category: int = 2  # 항상 2로 고정
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
        "주어진 좌표와 location 정보를 기반으로 구글맵에서 식당의 title, rating, reviews, latitude, longitude를 검색합니다."
    )

    def _run(self, location: str, coordinates: str) -> List[Dict]:
        url = "https://serpapi.com/search"
        all_candidates = []
        for start in [0, 20]:
            params = {
                "engine": "google_maps",
                "q": f"{location} 맛집",
                "ll": f"@{coordinates},14z",
                "hl": "ko",
                "gl": "kr",
                "api_key": SERPAPI_API_KEY,
                "start": start,
            }
            try:
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                candidates = [
                    {
                        "title": r["title"],
                        "rating": r.get("rating", 0),
                        "reviews": r.get("reviews", 0),
                        "latitude": r.get("gps_coordinates", {}).get("latitude", None),
                        "longitude": r.get("gps_coordinates", {}).get(
                            "longitude", None
                        ),
                    }
                    for r in data.get("local_results", [])
                ]
                all_candidates.extend(candidates)
            except Exception as e:
                print(f"[RestaurantBasicSearchTool] Error at start={start}: {e}")
        return all_candidates


# 맛집 필터링 도구
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


# 네이버 웹 검색 도구
class NaverWebSearchTool(BaseTool):
    name: str = "NaverWebSearch"
    description: str = (
        "네이버 웹 검색 API를 사용해 식당의 텍스트 기반 세부 정보를 검색합니다."
    )

    def _run(self, query: str) -> Dict:
        if not AGENT_NAVER_CLIENT_ID or not AGENT_NAVER_CLIENT_SECRET:
            return {"error": "네이버 API 자격 증명이 없습니다."}

        url = "https://openapi.naver.com/v1/search/webkr.json"
        headers = {
            "X-Naver-Client-Id": AGENT_NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": AGENT_NAVER_CLIENT_SECRET,
        }
        params = {"query": query, "display": 1, "start": 1, "sort": "random"}
        try:
            resp = requests.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            if not items:
                return {"description": "정보 없음."}

            return {
                "description": items[0].get("description", "정보 없음."),
                "url": items[0].get("link", ""),
            }
        except Exception as e:
            return {"error": str(e)}


# 네이버 이미지 검색 도구
class NaverImageSearchTool(BaseTool):
    name: str = "NaverImageSearch"
    description: str = (
        "네이버 이미지 검색 API를 사용해 식당에 맞는 이미지 URL을 검색합니다."
    )

    def _run(self, query: str) -> str:
        if not AGENT_NAVER_CLIENT_ID or not AGENT_NAVER_CLIENT_SECRET:
            return ""

        url = "https://openapi.naver.com/v1/search/image"
        headers = {
            "X-Naver-Client-Id": AGENT_NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": AGENT_NAVER_CLIENT_SECRET,
        }
        params = {"query": query, "display": 1, "sort": "sim"}
        try:
            resp = requests.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            return items[0].get("link", "") if items else ""
        except Exception as e:
            return ""


# 최종 추천 생성 도구
class FinalRecommendationTool(BaseTool):
    name: str = "FinalRecommendationTool"
    description: str = (
        "필터링된 맛집 후보, 네이버 텍스트 기반 세부 정보와 여행 계획(TravelPlan)을 고려하여 최종 맛집 추천 리스트를 생성합니다."
    )

    def _run(self, inputs: Dict) -> Dict:
        filtered_list = inputs.get("filtered_list", [])
        text_details_map = inputs.get("text_details_map", {})
        image_map = inputs.get("image_map", {})
        travel_plan = inputs.get("travel_plan", {})

        start_date = datetime.strptime(travel_plan.get("start_date"), "%Y-%m-%d")
        end_date = datetime.strptime(travel_plan.get("end_date"), "%Y-%m-%d")
        num_days = (end_date - start_date).days + 1  # 여행 일정의 총 일수 계산

        day_x = 1
        order = 1
        spots = []

        for idx, restaurant in enumerate(filtered_list):
            name = restaurant["title"]
            description_data = text_details_map.get(name, {})
            image_url = image_map.get(name, "")

            spot_time = (
                "08:00 AM" if order == 1 else "12:00 PM" if order == 2 else "07:00 PM"
            )

            spots.append(
                spot_pydantic(
                    kor_name=name,
                    eng_name=description_data.get("eng_name", None),
                    description=description_data.get("description", "정보 없음."),
                    address=description_data.get("address", "주소 없음."),
                    latitude=str(restaurant["latitude"]),
                    longitude=str(restaurant["longitude"]),
                    url=description_data.get("url", ""),
                    image_url=image_url,
                    map_url=f"https://www.google.com/maps/search/?api=1&query={restaurant['latitude']},{restaurant['longitude']}",
                    spot_category=2,
                    phone_number=description_data.get("phone_number", None),
                    business_status=description_data.get("business_status", None),
                    business_hours=description_data.get("business_hours", None),
                    order=order,
                    day_x=day_x,
                    spot_time=spot_time,
                )
            )

            if order == 3:
                order = 1
                if day_x < num_days:  # 여행 일정 범위 내에서만 증가
                    day_x += 1
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
    backstory="나는 맛집 데이터 분석 전문가로, Google Maps API를 사용하여 특정 위치(예: 부산광역시)의 식당 정보를 조회한다.",
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
    goal="필터링된 맛집 후보와 네이버 텍스트 기반 세부 정보를, 여행 계획을 고려하여 최종 맛집 추천 리스트를 생성한다.",
    backstory="나는 데이터 구조화 전문가로, 후보 식당의 기본 정보, 네이버에서 수집한 텍스트 세부 정보와 여행 계획 정보를 종합하여 최종 추천 리스트를 구성한다.",
    tools=[FinalRecommendationTool()],
    llm=llm,
    verbose=True,
    output_pydantic=spots_pydantic,
)


# ------------------------- Task & Crew ------------------------------
def create_recommendation(input_data: dict) -> dict:
    try:
        travel_plan = TravelPlan(**input_data)
        tasks = [
            Task(
                description="좌표 조회",
                agent=geocoding_agent,
                expected_output="{'location': '부산광역시', 'coordinates': '35.1796,129.0756'}",
            ),
            Task(
                description="맛집 기본 조회",
                agent=restaurant_basic_search_agent,
                expected_output="리스트 형태로 title, rating, reviews, latitude, longitude 정보를 포함한 맛집 리스트",
            ),
            Task(
                description="맛집 필터링",
                agent=restaurant_filter_agent,
                expected_output="평점 4.0 이상, 리뷰 500개 이상인 맛집 리스트",
            ),
            Task(
                description="세부 정보 조회 (네이버 텍스트)",
                agent=naver_web_search_agent,
                expected_output="각 식당의 네이버 웹 검색 결과에서 세부 정보 (주소, 설명, 전화번호 등) 포함",
            ),
            Task(
                description="이미지 정보 조회 (네이버 이미지)",
                agent=naver_image_search_agent,
                expected_output="각 식당의 대표 이미지 URL",
            ),
            Task(
                description="최종 추천 생성",
                agent=final_recommendation_agent,
                expected_output="spot_pydantic 구조를 따르는 최종 추천 리스트",
            ),
        ]

        crew = Crew(
            agents=[
                geocoding_agent,
                restaurant_basic_search_agent,
                restaurant_filter_agent,
                naver_web_search_agent,
                naver_image_search_agent,
                final_recommendation_agent,
            ],
            tasks=tasks,
            verbose=True,
        )

        result = crew.kickoff()
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# FastAPI 엔드포인트 정의
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
