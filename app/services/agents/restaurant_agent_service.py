import traceback
import os
import requests
import json
from crewai import Agent, Task, Crew, LLM
from datetime import datetime
from dotenv import load_dotenv
from crewai.tools import BaseTool
from pydantic import BaseModel
from typing import List, Dict, Type

# 환경 변수 로드
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
GOOGLE_MAP_API_KEY = os.getenv("GOOGLE_MAP_API_KEY")


# -------------------------------------------------------------------
# 1. 사용자 여행 데이터 입력 스키마
class TravelPlan(BaseModel):
    main_location: str
    start_date: str
    end_date: str
    companion_count: int
    concepts: List[str]


# 추가: RestaurantSearchTool용 인자 스키마
class RestaurantSearchArgs(BaseModel):
    location: str
    coordinates: str


# -------------------------------------------------------------------
# 2. 좌표 조회 툴 (Geocoding API 활용)
class GeocodingTool(BaseTool):
    name: str = "GeocodingTool"
    description: str = (
        "Google Geocoding API를 사용하여 주어진 위치의 위도와 경도를 반환합니다."
    )

    def _run(self, location: str) -> str:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": location, "key": GOOGLE_MAP_API_KEY}
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("results"):
                loc = data["results"][0]["geometry"]["location"]
                return f"{loc['lat']},{loc['lng']}"
            else:
                return ""
        except Exception as e:
            return f"[GeocodingTool] Error: {str(e)}"


# 좌표 조회 에이전트 생성
geocoding_agent = Agent(
    role="좌표 조회 전문가",
    goal="사용자 입력 위치의 위도와 경도를 정확히 조회한다.",
    tools=[GeocodingTool()],
    llm=LLM(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY),
    verbose=True,
)


# -------------------------------------------------------------------
# 3. 맛집 기본 정보 조회 (평점, 리뷰 수만 가져옴)
class RestaurantBasicSearchTool(BaseTool):
    name: str = "RestaurantBasicSearchTool"
    description: str = (
        "주어진 좌표를 기반으로 평점과 리뷰 수만 포함된 식당 리스트를 검색합니다."
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
                        "place_id": r.get("place_id", ""),
                    }
                    for r in data.get("local_results", [])
                ]
                all_candidates.extend(candidates)
            except Exception as e:
                print(f"[RestaurantBasicSearchTool] Error at start={start}: {e}")
        return all_candidates


# 맛집 후보 조회 에이전트 생성
restaurant_basic_search_agent = Agent(
    role="맛집 기본 조회 전문가",
    goal="좌표 정보를 활용하여 맛집의 평점과 리뷰 수를 조회한다.",
    tools=[RestaurantBasicSearchTool()],
    llm=LLM(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY),
    verbose=True,
)


# -------------------------------------------------------------------
# 5. 최종 추천 생성 툴 (엄격한 JSON 형식 프롬프트 적용)
class FinalRecommendationTool(BaseTool):
    name: str = "FinalRecommendationTool"
    description: str = (
        "필터링된 맛집 리스트를 기반으로 최종 추천 맛집 리스트를 엄격한 JSON 형식으로 생성합니다."
    )

    def _run(self, filtered_list: List[Dict]) -> Dict:
        if not isinstance(filtered_list, list):
            return {"error": "잘못된 입력 형식"}

        structured_response = {"Spots": []}
        for idx, restaurant in enumerate(filtered_list[:6]):
            structured_response["Spots"].append(
                {
                    "kor_name": restaurant.get("kor_name", ""),
                    "eng_name": restaurant.get("eng_name", ""),
                    "description": restaurant.get("description", ""),
                    "address": restaurant.get("address", ""),
                    "zip": restaurant.get("zip", ""),
                    "url": restaurant.get("url", ""),
                    "image_url": restaurant.get("image_url", ""),
                    "map_url": restaurant.get("map_url", ""),
                    "likes": restaurant.get("likes", 0),
                    "satisfaction": restaurant.get("satisfaction", 0),
                    "spot_category": restaurant.get("spot_category", 0),
                    "phone_number": restaurant.get("phone_number", ""),
                    "business_status": restaurant.get("business_status", True),
                    "business_hours": restaurant.get("business_hours", ""),
                    "day_x": 1 if idx < 3 else 2,
                    "order": (idx % 3) + 1,
                    "spot_time": (
                        "2025-02-01T09:00:00" if idx < 3 else "2025-02-02T09:00:00"
                    ),
                }
            )
        return structured_response


final_recommendation_agent = Agent(
    role="최종 추천 에이전트",
    goal="필터링된 맛집 후보 리스트를 바탕으로 최종 추천 맛집 리스트를 엄격한 JSON 형식으로 생성한다.",
    tools=[FinalRecommendationTool()],
    llm=LLM(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY),
    verbose=True,
)


# -------------------------------------------------------------------
# 6. 전체 Crew 구성 및 실행 함수
def create_recommendation(input_data: dict) -> dict:
    try:
        travel_plan = TravelPlan(**input_data)
        location = travel_plan.main_location

        crew = Crew(
            agents=[
                geocoding_agent,
                restaurant_basic_search_agent,
                restaurant_filter_agent,
                final_recommendation_agent,
            ],
            tasks=[
                Task(description="좌표 조회", agent=geocoding_agent),
                Task(description="맛집 기본 조회", agent=restaurant_basic_search_agent),
                Task(description="맛집 필터링", agent=restaurant_filter_agent),
                Task(description="최종 추천 생성", agent=final_recommendation_agent),
            ],
            verbose=True,
        )

        final_result = crew.kickoff()
        return final_result

    except Exception as e:
        print(f"[ERROR] {e}")
        traceback.print_exc()
        return {"message": "요청 처리 중 오류가 발생했습니다.", "error": str(e)}


if __name__ == "__main__":
    test_input = {
        "main_location": "부산광역시",
        "start_date": "2025-02-01T00:00:00",
        "end_date": "2025-02-02T00:00:00",
        "companion_count": 3,
        "concepts": ["가족", "맛집"],
        "name": "부산 여행 일정",
    }
    result = create_recommendation(test_input)
    print(json.dumps(result, ensure_ascii=False, indent=2))
