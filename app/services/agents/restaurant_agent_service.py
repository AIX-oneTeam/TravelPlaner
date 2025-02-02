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

# 공통 LLM 설정
llm = LLM(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY)

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
    backstory="""
    나는 위치 데이터 전문가로, 지도 서비스와 공간 데이터 분석에 능숙하다. 
    Google Geocoding API를 활용하여 입력된 장소의 위도와 경도를 정확하게 조회한다. 
    신뢰할 수 있는 위치 정보를 빠르게 제공하는 것이 나의 핵심 역할이다.
    """,
    tools=[GeocodingTool()],
    llm=llm,
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
    backstory="""
    나는 맛집 데이터 분석 전문가로, 다양한 위치 기반 서비스를 활용해 신뢰할 수 있는 정보를 제공한다. 
    Google Maps API를 사용하여 특정 위치의 맛집 평점과 리뷰 수를 정확하게 조회한다. 
    사용자가 보다 나은 선택을 할 수 있도록 핵심 데이터를 빠르게 제공하는 것이 나의 역할이다.
    """,
    tools=[RestaurantBasicSearchTool()],
    llm=llm,
    verbose=True,
)

# -------------------------------------------------------------------
# 4. 맛집 필터링 툴 (평점과 리뷰 수 기반 필터링)
class RestaurantFilterTool(BaseTool):
    name: str = "RestaurantFilterTool"
    description: str = (
        "조회된 맛집 리스트 중 평점 4점 이상, 리뷰 500개 이상인 식당만 필터링합니다."
    )

    def _run(self, candidates: List[Dict]) -> List[Dict]:
        return [
            r
            for r in candidates
            if r.get("rating", 0) >= 4.0 and r.get("reviews", 0) >= 500
        ]

restaurant_filter_agent = Agent(
    role="맛집 필터링 전문가",
    goal="평점 4.0 이상, 리뷰 500개 이상인 식당을 선별한다.",
    backstory="""
    나는 데이터 필터링 전문가로, 맛집 리뷰와 평점을 분석하여 신뢰할 수 있는 식당만 선별한다. 
    특정 기준을 충족하는 식당을 정확하게 추려내어 사용자에게 최상의 선택지를 제공한다. 
    객관적인 데이터 기반으로 품질 높은 맛집 정보를 추천하는 것이 나의 역할이다.
    """,
    tools=[RestaurantFilterTool()],
    llm=llm,
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
                    "spot_time": ("2025-02-01" if idx < 3 else "2025-02-02"),
                }
            )
        return structured_response


final_recommendation_agent = Agent(
    role="최종 추천 에이전트",
    goal="필터링된 맛집 후보 리스트를 바탕으로 최종 추천 맛집 리스트를 엄격한 JSON 형식으로 생성한다.",
    backstory="""
    나는 데이터 구조화 전문가로, 필터링된 맛집 정보를 체계적으로 정리하는 역할을 한다. 
    사용자에게 최적의 맛집을 제공하기 위해 엄격한 JSON 형식을 유지하며 일관된 데이터를 생성한다. 
    명확하고 활용하기 쉬운 추천 리스트를 구성하는 것이 나의 핵심 목표이다.
    """,
    tools=[FinalRecommendationTool()],
    llm=llm,
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
                Task(
                    description="좌표 조회",
                    agent=geocoding_agent,
                    expected_output="위도,경도 형식의 문자열",
                ),
                Task(
                    description="맛집 기본 조회",
                    agent=restaurant_basic_search_agent,
                    expected_output="평점과 리뷰 수를 포함한 맛집 리스트",
                ),
                Task(
                    description="맛집 필터링",
                    agent=restaurant_filter_agent,
                    expected_output="평점 4.0 이상, 리뷰 500개 이상인 필터링된 맛집 리스트",
                ),
                Task(
                    description="최종 추천 생성",
                    agent=final_recommendation_agent,
                    expected_output="엄격한 JSON 형식의 추천 맛집 리스트",
                ),
            ],
            verbose=True,
        )

        final_result = crew.kickoff()

        # JSON 변환을 위한 직렬화 처리 함수
        def serialize(obj):
            """객체를 JSON 직렬화 가능하도록 변환"""
            if isinstance(obj, (dict, list, str, int, float, bool, type(None))):
                return obj  # 기본 데이터 타입은 그대로 반환
            elif hasattr(obj, "__dict__"):
                return {
                    key: serialize(value) for key, value in vars(obj).items()
                }  # 객체를 딕셔너리로 변환
            elif isinstance(obj, list):
                return [serialize(item) for item in obj]  # 리스트 내부 요소 변환
            else:
                return str(obj)  # 변환할 수 없는 경우 문자열 변환

        return serialize(final_result)

    except Exception as e:
        print(f"[ERROR] {e}")
        traceback.print_exc()
        return {"message": "요청 처리 중 오류가 발생했습니다.", "error": str(e)}


# -------------------------------------------------------------------
# 테스트 실행
if __name__ == "__main__":
    test_input = {
        "main_location": "부산광역시",
        "start_date": "2025-02-01",
        "end_date": "2025-02-02",
        "companion_count": 3,
        "concepts": ["가족", "맛집"],
        "name": "부산 여행 일정",
    }
    result = create_recommendation(test_input)
    print(json.dumps(result, ensure_ascii=False, indent=2))
