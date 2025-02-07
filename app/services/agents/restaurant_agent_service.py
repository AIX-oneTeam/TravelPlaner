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
GOOGLE_MAP_API_KEY = os.getenv("GOOGLE_MAP_API_KEY")
AGENT_NAVER_CLIENT_ID = os.getenv("AGENT_NAVER_CLIENT_ID")
AGENT_NAVER_CLIENT_SECRET = os.getenv("AGENT_NAVER_CLIENT_SECRET")

llm = LLM(model="gpt-4o", temperature=0, api_key=OPENAI_API_KEY)


class spot_pydantic(BaseModel):
    kor_name: str = Field(max_length=255)
    eng_name: str = Field(default=None, max_length=255)
    description: str = Field(max_length=255)
    address: str = Field(max_length=255)
    url: str = Field(default=None, max_length=2083)
    image_url: str = Field(max_length=2083)
    map_url: str = Field(max_length=2083)
    latitude: float = Field(...)  # SQLAlchemy 관련 인자는 제거
    longitude: float = Field(...)
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
            next_page_token = data.get("next_page_token")
            if next_page_token:
                max_retries = 1
                for _ in range(max_retries):
                    try:
                        time.sleep(3)
                        params["pagetoken"] = next_page_token
                        response = requests.get(url, params=params)
                        response.raise_for_status()
                        data = response.json()
                        second_results = data.get("results", [])[:10]
                        print(f"두 번째 요청 결과 수: {len(second_results)}")
                        for place in second_results:
                            if len(all_candidates) >= 40:
                                break
                            place_id = place.get("place_id")
                            if place_id:
                                details = self.get_place_details(place_id)
                                if details:
                                    all_candidates.append(details)
                        break
                    except Exception as e:
                        print(f"Token retry error: {e}")
                        if _ == max_retries - 1:
                            raise
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
            r for r in candidates
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
        params = {"query": f"{query}", "display": 3, "start": 1, "sort": "sim"}
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
            if not items:
                return {"description": "정보를 찾을 수 없습니다.", "url": ""}
            descriptions = []
            for item in items:
                desc = item.get("description", "").strip()
                if desc and len(desc) > 30:
                    descriptions.append(desc)
            combined_description = " ".join(descriptions)
            return {
                "description": combined_description[:200] if len(combined_description) > 200 else combined_description,
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
    description: str = "네이버 이미지 검색 API를 사용해 식당의 대표 이미지를 검색합니다."

    def fetch(self, query: str):
        url = "https://openapi.naver.com/v1/search/image"
        headers = {
            "X-Naver-Client-Id": AGENT_NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": AGENT_NAVER_CLIENT_SECRET,
        }
        params = {"query": f"{query}", "display": 1, "sort": "sim", "filter": "large"}
        try:
            response = requests.get(url, headers=headers, params=params)
            data = response.json()
            items = data.get("items", [])
            if not items:
                return "https://via.placeholder.com/300x200?text=No+Image"
            return items[0].get("link", "https://via.placeholder.com/300x200?text=No+Image")
        except Exception as e:
            print(f"네이버 이미지 검색 오류: {str(e)}")
            return "https://via.placeholder.com/300x200?text=Error"

    def _run(self, restaurant_list: List[str]) -> Dict[str, str]:
        results = {}
        for restaurant in restaurant_list:
            results[restaurant] = self.fetch(restaurant)
        return results


# ------------------------- Agent ------------------------------
geocoding_agent = Agent(
    role="좌표 조회 전문가",
    goal="사용자가 입력한 location(예: '부산광역시')의 위도와 경도를 조회하며, location 값은 그대로 유지한다.",
    backstory="나는 위치 데이터 전문가로, 입력된 location 값을 변경하지 않고 Google Geocoding API를 통해 좌표를 조회한다.",
    tools=[GeocodingTool()],
    llm=llm,
    verbose=True,
)

restaurant_basic_search_agent = Agent(
    role="맛집 기본 조회 전문가",
    goal="좌표 정보를 활용하여 식당의 기본 정보(구글맵의 title, rating, reviews, 위도, 경도)를 조회한다.",
    backstory="나는 맛집 데이터 분석 전문가로, Google Maps API를 사용하여 특정 위치의 식당 정보를 최대 40개까지 조회한다.",
    tools=[RestaurantBasicSearchTool()],
    llm=llm,
    verbose=True,
)

restaurant_filter_agent = Agent(
    role="맛집 필터링 전문가",
    goal="평점과 리뷰 수 기준으로 식당 후보를 선별한다.",
    backstory="나는 데이터 필터링 전문가로, 맛집 리뷰와 평점을 분석하여 신뢰할 수 있는 식당 후보를 추려낸다.",
    tools=[RestaurantFilterTool()],
    llm=llm,
    verbose=True,
)

naver_web_search_agent = Agent(
    role="네이버 웹 검색 에이전트",
    goal="네이버 웹 검색 API를 사용해 식당의 텍스트 기반 세부 정보를 조회한다.",
    backstory="나는 네이버 웹 검색 전문가로, 식당의 상세 텍스트 정보를 제공합니다. 최신 검색 기술과 데이터를 활용하여 정확하고 신뢰할 수 있는 식당 정보를 제공합니다.",
    tools=[NaverWebSearchTool()],
    llm=llm,
    verbose=True,
)

naver_image_search_agent = Agent(
    role="네이버 이미지 검색 에이전트",
    goal="네이버 이미지 검색 API를 사용해 식당의 이미지 URL을 조회한다.",
    backstory="나는 네이버 이미지 검색 전문가로, 식당의 정확한 이미지를 제공합니다.",
    tools=[NaverImageSearchTool()],
    llm=llm,
    verbose=True,
)

final_recommendation_agent = Agent(
    role="최종 추천 에이전트",
    goal="필터링된 맛집 후보와 네이버 텍스트 기반 세부 정보를, 여행 계획을 고려하여 최종 맛집 추천 리스트를 생성한다.",
    backstory="나는 데이터 구조화 전문가로, 후보 식당의 기본 정보, 네이버에서 수집한 텍스트 세부 정보와 여행 계획 정보를 종합하여 최종 추천 리스트를 구성한다.",
    tools=[NaverWebSearchTool()],
    llm=llm,
    verbose=True,
)


# ------------------------- Task & Crew ------------------------------
async def create_recommendation(input_data: dict) -> dict:
    try:
        print(f"[입력 데이터] input_data: {input_data}")  # 받은 데이터 확인

        prompt_text = f'추가 참고: "{input_data["prompt"]}" 도 참고하여 추천해주세요.\n' if input_data.get("prompt") else ""
        print(f"[프롬프트 입력] input_data: {prompt_text}")

        tasks = [
            Task(
                description=f"{input_data['main_location']}의 좌표 조회",
                agent=geocoding_agent,
                expected_output="위치 좌표",
            ),
            Task(
                description="맛집 기본 정보 조회",
                agent=restaurant_basic_search_agent,
                expected_output="맛집 기본 정보 리스트",
            ),
            Task(
                description="맛집 필터링 (평점 4.0 이상, 리뷰 500개 이상)",
                agent=restaurant_filter_agent,
                expected_output="필터링된 맛집 리스트",
            ),
            Task(
                description=(
                    f"이전 단계에서 평점 4.0 이상, 리뷰 수 500개 이상으로 필터링된 {input_data['main_location']} 지역의 맛집 후보 리스트를 바탕으로, 각 식당의 "
                    "세부 정보를 최신 검색 결과를 활용하여 가져오라. "
                    "검색 시 반드시 아래 JSON 스키마에 맞추어 정확하고 누락 없이 정보를 반환할 것. "
                    "특히, 아래 항목들은 최신 정보에 기반하여 모두 포함되어야 한다:\n\n"
                    "{\n"
                    '  "kor_name": "string (가게 한글이름, 최대 255자)",\n'
                    '  "eng_name": "string 또는 null (가게 영어이름, 최대 255자)",\n'
                    '  "description": "string (가게 설명, 최대 255자)",\n'
                    '  "address": "string (주소, 최대 255자)",\n'
                    '  "url": "string 또는 null (웹사이트 URL, 최대 2083자)",\n'
                    '  "image_url": "string (이미지 URL, 최대 2083자)",\n'
                    '  "map_url": "string (map_url, 최대 2083자)",\n'
                    '  "latitude": "number (위도)",\n'
                    '  "longitude": "number (경도)",\n'
                    '  "spot_category": "2",\n'
                    '  "phone_number": "string 또는 null (전화번호, 최대 300자)",\n'
                    '  "business_status": "string 또는 null (영업 상태)",\n'
                    '  "business_hours": "string 또는 null (영업시간, 최대 255자)",\n'
                    "}\n\n"
                    "위 JSON 스키마에 맞추어 모든 필드를 채워서 결과를 반환하라."
                ),
                agent=naver_web_search_agent,
                expected_output="각 후보 식당의 세부 정보(가게 한글이름, 영어이름, 설명, 주소, 웹사이트 URL, 이미지 URL, map_url, 위도, 경도, 스팟 카테고리, 전화번호, 영업 상태, 영업시간)를 포함하는 details_map",
            ),
            Task(
                description="네이버 이미지 검색으로 맛집 이미지 수집",
                agent=naver_image_search_agent,
                expected_output="맛집 이미지 URL",
            ),
            Task(
                description=(
                    f"이전 단계에서 수집한 {input_data['main_location']} 지역의 맛집 데이터를 바탕으로, "
                    f"{input_data['start_date']}부터 {input_data['end_date']}까지 여행하는 {input_data['ages']} 연령대의 고객과 "
                    f"동반자({', '.join(map(lambda c: c['label'] + ' ' + str(c['count']) + '명', input_data['companion_count']))})의 "
                    f"{', '.join(input_data['concepts'])} 컨셉에 맞는 최종 맛집 리스트를 중복없이 추천하라. "
                    f"{prompt_text}"
                    "필수:\n"
                    "- spot_category는 2로 고정한다.\n"
                    "- day_x는 가게가 추천되는 날을 의미한다. (예: 1일차, 2일차 등)\n"
                    "- order는 해당 day_x에서 가게가 추천되는 순서를 의미한다. (아침이면 1, 점심이면 2, 저녁이면 3)\n"
                    "- spot_time은 아침, 점심, 저녁 시간대를 hh:mm:ss 형식으로 표시해야 한다.\n"
                    "- order와 day_x는 사용자의 여행 일정 일수에 맞게 조정되어야 한다.\n"
                    "- 최종 맛집 리스트의 개수는 하루 3끼 기준으로 결정된다. 예를 들어, 1박 2일이면 총 6개, 2박 3일이면 총 8개 이상 출력되어야 한다.\n"
                    "- 위도, 경도, 이미지 데이터는 이전 태스크들에서 얻은 정보를 가져와서 입력한다."
                ),
                agent=final_recommendation_agent,
                expected_output="최종 추천 맛집 리스트",
                output_pydantic=spots_pydantic,
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

        if hasattr(result, "tasks_output") and result.tasks_output:
            final_task_output = result.tasks_output[-1]
            if hasattr(final_task_output, "pydantic"):
                spots_data = final_task_output.pydantic.model_dump()
            else:
                spots_data = json.loads(final_task_output.raw)
        else:
            spots_data = {"spots": []}

        restaurant_response = {
            "message": "요청이 성공적으로 처리되었습니다.",
            "plan": {
                "name": input_data.get("name", "여행 일정"),
                "start_date": input_data["start_date"],
                "end_date": input_data["end_date"],
                "main_location": input_data["main_location"],
                "ages": input_data.get("ages", 0),
                "companion_count": sum(c.get("count", 0) for c in input_data.get("companion_count", [])),
                "concepts": ", ".join(input_data.get("concepts", [])),
                "member_id": input_data.get("member_id", 0),
                "created_at": datetime.now().strftime("%Y-%m-%d"),
                "updated_at": datetime.now().strftime("%Y-%m-%d"),
            },
            "spots": spots_data.get("spots", []),
        }

        return restaurant_response

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
