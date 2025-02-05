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
import time

app = FastAPI()

# 환경 변수 로드
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
GOOGLE_MAP_API_KEY = os.getenv("GOOGLE_MAP_API_KEY")
AGENT_NAVER_CLIENT_ID = os.getenv("AGENT_NAVER_CLIENT_ID")
AGENT_NAVER_CLIENT_SECRET = os.getenv("AGENT_NAVER_CLIENT_SECRET")

llm = LLM(model="gpt-3.5-turbo", temperature=0, api_key=OPENAI_API_KEY)

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

        params = {
            "query": f"{location} 맛집",
            "language": "ko",
            "type": "restaurant",
            "location": f"{lat},{lng}",
            "radius": "5000",
            "key": GOOGLE_MAP_API_KEY,
        }

        try:
            # 첫 20개 요청
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            print(f"첫 요청 결과 수: {len(data.get('results', []))}")

            for place in data.get("results", []):
                place_id = place.get("place_id")
                if place_id:
                    details = self.get_place_details(place_id)
                    if details:
                        all_candidates.append(details)

            # 추가 20개 요청을 위한 반복 시도
            next_page_token = data.get("next_page_token")
            if next_page_token:
                max_retries = 3
                for _ in range(max_retries):
                    try:
                        time.sleep(5)
                        params["pagetoken"] = next_page_token
                        response = requests.get(url, params=params)
                        response.raise_for_status()
                        data = response.json()
                        print(f"두 번째 요청 결과 수: {len(data.get('results', []))}")

                        for place in data.get("results", []):
                            if len(all_candidates) >= 40:
                                break
                            place_id = place.get("place_id")
                            if place_id:
                                details = self.get_place_details(place_id)
                                if details:
                                    all_candidates.append(details)
                        break  # 성공하면 반복 중단
                    except Exception as e:
                        print(f"Token retry error: {e}")
                        if _ == max_retries - 1:  # 마지막 시도였다면
                            raise  # 에러 발생

            print(f"최종 수집된 맛집 수: {len(all_candidates)}")

        except Exception as e:
            print(f"[RestaurantBasicSearchTool] Search Error: {e}")

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


class NaverWebSearchTool(BaseTool):
    name: str = "NaverWebSearch"
    description: str = "네이버 웹 검색 API를 사용해 식당의 상세 정보를 검색합니다."

    def fetch(self, query: str):
        url = "https://openapi.naver.com/v1/search/webkr.json"
        headers = {
            "X-Naver-Client-Id": AGENT_NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": AGENT_NAVER_CLIENT_SECRET,
        }
        params = {
            "query": f"{query}",  # 검색어 최적화
            "display": 3,  # 결과 수를 3개로 증가
            "start": 1,
            "sort": "sim",  # 정확도순 정렬
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])

            if not items:
                return {"description": "정보를 찾을 수 없습니다.", "url": ""}

            # 여러 검색 결과를 조합하여 더 풍부한 설명 생성
            descriptions = []
            for item in items:
                desc = item.get("description", "").strip()
                if desc and len(desc) > 30:  # 의미있는 설명만 추가
                    descriptions.append(desc)

            combined_description = " ".join(descriptions)

            return {
                "description": (
                    combined_description[:200]
                    if len(combined_description) > 200
                    else combined_description
                ),
                "url": items[0].get("link", "") if items else "",
            }
        except Exception as e:
            print(f"네이버 웹 검색 오류: {str(e)}")
            return {"description": "정보 없음", "url": ""}

    def _run(self, restaurant_list: List[str]) -> Dict[str, Dict[str, str]]:
        results = {}
        for restaurant in restaurant_list:
            results[restaurant] = self.fetch(restaurant)
        return results


class NaverImageSearchTool(BaseTool):
    name: str = "NaverImageSearch"
    description: str = (
        "네이버 이미지 검색 API를 사용해 식당의 대표 이미지를 검색합니다."
    )

    def fetch(self, query: str):
        url = "https://openapi.naver.com/v1/search/image"
        headers = {
            "X-Naver-Client-Id": AGENT_NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": AGENT_NAVER_CLIENT_SECRET,
        }
        params = {
            "query": f"{query}",  # 검색어 최적화
            "display": 1,
            "sort": "sim",
            "filter": "large",  # 고품질 이미지 필터링
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            data = response.json()
            items = data.get("items", [])
            if not items:
                return "https://via.placeholder.com/300x200?text=No+Image"
            return items[0].get(
                "link", "https://via.placeholder.com/300x200?text=No+Image"
            )
        except Exception as e:
            print(f"네이버 이미지 검색 오류: {str(e)}")
            return "https://via.placeholder.com/300x200?text=Error"

    def _run(self, restaurant_list: List[str]) -> Dict[str, str]:
        results = {}
        for restaurant in restaurant_list:
            results[restaurant] = self.fetch(restaurant)
        return results

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
    goal="필터링된 맛집 후보와 네이버 텍스트 기반 세부 정보를, 여행 계획을 고려하여 최종 맛집 추천 리스트를 생성한다.",
    backstory="나는 데이터 구조화 전문가로, 후보 식당의 기본 정보, 네이버에서 수집한 텍스트 세부 정보와 여행 계획 정보를 종합하여 최종 추천 리스트를 구성한다.",
    tools=[NaverWebSearchTool()],
    llm=llm,
    verbose=True,
)


# ------------------------- Task & Crew ------------------------------
def create_recommendation(input_data: dict) -> dict:
    try:
        print(f"[DEBUG3] input_data: {input_data}")  # 받은 데이터 확인

        # Task 정의
        tasks = [
            Task(
                description=f"{input_data['main_location']}의 좌표 조회",
                agent=geocoding_agent,
                expected_output="위치 좌표",
                config={"location": input_data["main_location"]},
            ),
            Task(
                description="맛집 기본 정보 조회",
                agent=restaurant_basic_search_agent,
                expected_output="맛집 기본 정보 리스트",
                config={},
            ),
            Task(
                description="맛집 필터링 (평점 4.0 이상, 리뷰 500개 이상)",
                agent=restaurant_filter_agent,
                expected_output="필터링된 맛집 리스트",
                config={},
            ),
            Task(
                description="세부 정보 조회",
                agent=naver_web_search_agent,
                expected_output="각 후보 식당의 세부 정보(연락처, 영업시간, 가격대, 웹사이트, 사진, 분류/타입, 비즈니스 상태)를 포함하는 details_map",
            ),
            Task(
                description="네이버 이미지 검색으로 맛집 이미지 수집",
                agent=naver_image_search_agent,
                expected_output="맛집 이미지 URL",
                config={},
            ),
            Task(
                description=(
                    f"이전 단계에서 수집한 {input_data['main_location']} 지역의 맛집 데이터를 바탕으로, "
                    f"{input_data['start_date']}부터 {input_data['end_date']}까지 여행하는 {input_data['ages']} 연령대의 고객과 "
                    f"동반자({', '.join([f'{c['label']} {c['count']}명' for c in input_data['companions']])})의 "
                    f"{', '.join(input_data['concepts'])} 컨셉에 맞는 최종 맛집 리스트를 추천하라."
                ),
                agent=final_recommendation_agent,
                expected_output="최종 추천 맛집 리스트",
                output_json=spots_pydantic,
                config={
                    "travel_plan": input_data,  # dict 그대로 사용
                    "previous_results": "이전 태스크 결과",
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
                final_recommendation_agent,
            ],
            verbose=True,
        )

        result = crew.kickoff()
        return result

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
