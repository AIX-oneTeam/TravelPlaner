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


# 추가: RestaurantSearchTool용 인자 스키마 (기본 정보 용)
class RestaurantSearchArgs(BaseModel):
    location: str
    coordinates: str


# -------------------------------------------------------------------
# 2. 좌표 조회 툴 (Google Geocoding API 활용)
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


geocoding_agent = Agent(
    role="좌표 조회 전문가",
    goal="사용자가 입력한 location(예: '부산광역시')의 위도와 경도를 조회하며, location 값은 그대로 유지한다.",
    backstory=""" 
    나는 위치 데이터 전문가로, 입력된 location 값을 변경하지 않고 Google Geocoding API를 통해 좌표를 조회한다.
    """,
    tools=[GeocodingTool()],
    llm=llm,
    verbose=True,
)


# -------------------------------------------------------------------
# 3. 맛집 기본 정보 조회 툴 (기본 정보: 가게 이름, 평점, 리뷰 수, place_id)
class RestaurantBasicSearchTool(BaseTool):
    name: str = "RestaurantBasicSearchTool"
    description: str = (
        "주어진 좌표와 location 정보를 기반으로 평점과 리뷰 수, 그리고 place_id를 포함한 식당 리스트를 검색합니다."
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


restaurant_basic_search_agent = Agent(
    role="맛집 기본 조회 전문가",
    goal="좌표 정보를 활용하여 식당의 기본 정보(가게 이름, 평점, 리뷰 수, place_id)를 조회한다.",
    backstory=""" 
    나는 맛집 데이터 분석 전문가로, Google Maps API를 사용하여 특정 위치(예: 부산광역시)의 식당 정보를 조회한다.
    """,
    tools=[RestaurantBasicSearchTool()],
    llm=llm,
    verbose=True,
)


# -------------------------------------------------------------------
# 4. 맛집 필터링 툴 (평점 4.0 이상, 리뷰 500개 이상 필터링)
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


restaurant_filter_agent = Agent(
    role="맛집 필터링 전문가",
    goal="평점과 리뷰 수 기준으로 식당 후보를 선별한다.",
    backstory=""" 
    나는 데이터 필터링 전문가로, 맛집 리뷰와 평점을 분석하여 신뢰할 수 있는 식당 후보를 추려낸다.
    """,
    tools=[RestaurantFilterTool()],
    llm=llm,
    verbose=True,
)


# -------------------------------------------------------------------
# [새로운 단계] 5. 식당 세부 정보 조회 툴 (Batch 방식)
# 새로운 Tool은 필터링된 후보들의 place_id 리스트를 받아, 각 식당에 대해 구글 플레이스 API(신규)를 호출합니다.
class BatchRestaurantDetailTool(BaseTool):
    name: str = "BatchRestaurantDetailTool"
    description: str = (
        "필터링된 식당 후보들의 place_id 리스트를 받아, 구글 플레이스 API(신규)를 통해 연락처, 영업시간, 가격대, 웹사이트, 사진, "
        "분류/타입, 비즈니스 상태 등의 세부 정보를 조회하여, 각 place_id별 정보를 반환합니다."
    )

    def _run(self, place_ids: List[str]) -> Dict:
        details_map = {}
        fields = "addressComponents,opening_hours,price_level,website,international_phone_number,photos,types,business_status"
        base_url = "https://places.googleapis.com/v1/places/"
        for pid in place_ids:
            url = f"{base_url}{pid}"
            params = {"fields": fields, "key": GOOGLE_MAP_API_KEY}
            try:
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                result = data.get("result", {})
                details = {
                    "address": " ".join(
                        [
                            comp.get("long_name", "")
                            for comp in result.get("addressComponents", [])
                        ]
                    ),
                    "opening_hours": result.get("opening_hours", {}).get(
                        "weekday_text", []
                    ),
                    "price_level": result.get("price_level", None),
                    "website": result.get("website", ""),
                    "phone_number": result.get("international_phone_number", ""),
                    "types": result.get("types", []),
                    "business_status": result.get("business_status", ""),
                    "image_url": "",  # 필요시 사진 처리 로직 추가
                }
            except Exception as e:
                details = {"error": str(e)}
            details_map[pid] = details
        return details_map


batch_detail_agent = Agent(
    role="맛집 세부 정보 전문가",
    goal="필터링된 식당 후보들의 place_id를 받아, 구글 플레이스 API(신규)를 통해 세부 정보를 조회한다.",
    backstory=""" 
    나는 식당 세부 정보를 전문적으로 수집하는 전문가입니다.
    구글 플레이스 API(신규)를 사용하여 주소, 영업시간, 가격대, 웹사이트, 사진, 분류/타입, 비즈니스 상태 등의 정보를 조회합니다.
    """,
    tools=[BatchRestaurantDetailTool()],
    llm=llm,
    verbose=True,
)


# 여기까지가 Part 1/2
# -------------------------------------------------------------------
# 6. 최종 추천 생성 툴 (세부 정보와 추가 정보를 포함하여 최종 추천 리스트 구성)
class FinalRecommendationTool(BaseTool):
    name: str = "FinalRecommendationTool"
    description: str = (
        "필터링된 맛집 후보와 각 식당의 세부 정보를 바탕으로, 사용자 여행 일정 데이터를 고려하여 최종 맛집 추천 리스트를 "
        "엄격한 JSON 형식으로 생성합니다. 각 장소는 day_x와 order 필드를 포함해야 하며, "
        "day_x는 1부터 시작하여 여행 기간의 각 날짜를, order는 0부터 시작하여 각 날짜 내 순서를 나타냅니다."
    )

    def _run(self, inputs: Dict) -> Dict:
        """
        inputs 예시:
        {
            "filtered_list": [...],  # 기본 정보만 있는 후보 리스트
            "details_map": {         # 각 식당의 place_id를 key로 세부 정보가 담긴 dict
                "place_id1": { ... },
                "place_id2": { ... },
                ...
            },
            "travel_plan": { ... }   # 사용자 여행 일정 데이터
        }
        """
        filtered_list = inputs.get("filtered_list", [])
        details_map = inputs.get("details_map", {})
        travel_plan = inputs.get("travel_plan", {})

        final_spots = []
        # 예: 최종 추천 대상은 필터링된 후보 중 상위 6개
        for idx, restaurant in enumerate(filtered_list[:6]):
            pid = restaurant.get("place_id", "")
            detail = details_map.get(pid, {})
            final_spots.append(
                {
                    "kor_name": restaurant.get("title", ""),
                    "eng_name": "",  # 필요 시 추가
                    "description": detail.get("description", "")
                    or f"Rating: {restaurant.get('rating', 0)}, Reviews: {restaurant.get('reviews', 0)}",
                    "address": detail.get("address", ""),
                    "zip": "",  # 별도 처리 필요
                    "url": detail.get("website", ""),
                    "image_url": detail.get("image_url", ""),
                    "map_url": "",  # 필요시 지도 링크 생성 로직 추가
                    "rating": restaurant.get("rating", 0),
                    "reviews": restaurant.get("reviews", 0),
                    "satisfaction": 0,
                    "spot_category": 3,  # 맛집
                    "phone_number": detail.get("phone_number", ""),
                    "business_status": detail.get("business_status", True),
                    "business_hours": detail.get("opening_hours", []),
                    "order": (idx % 3) + 1,
                    "day_x": 1 if idx < 3 else 2,
                    "spot_time": ("2025-02-01" if idx < 3 else "2025-02-02"),
                }
            )
        return {"Spots": final_spots}


final_recommendation_agent = Agent(
    role="최종 추천 에이전트",
    goal="필터링된 맛집 후보와 세부 정보를 결합하여 최종 추천 맛집 리스트를 생성한다.",
    backstory=""" 
    나는 데이터 구조화 전문가로, 후보 식당의 기본 정보와 세부 정보를 종합하여 사용자 여행 일정과 선호도를 반영한 최종 맛집 추천 리스트를 구성한다.
    각 장소는 day_x와 order 필드를 포함해야 하며, day_x는 1부터 시작하여 각 날짜를, order는 0부터 시작하여 각 날짜 내 순서를 나타낸다.
    """,
    tools=[FinalRecommendationTool()],
    llm=llm,
    verbose=True,
)


# -------------------------------------------------------------------
# 7. 전체 Crew 구성 및 실행 함수
def create_recommendation(input_data: dict) -> dict:
    try:
        travel_plan = TravelPlan(**input_data)
        location = travel_plan.main_location

        # Crew 구성: Task 객체들을 순차적으로 실행 (Crew.kickoff 사용)
        tasks = [
            Task(
                description="좌표 조회",
                agent=geocoding_agent,
                expected_output="{'location': '부산광역시', 'coordinates': '...'}",
            ),
            Task(
                description="맛집 기본 조회",
                agent=restaurant_basic_search_agent,
                expected_output="기본 정보(가게 이름, 평점, 리뷰 수, place_id)를 포함한 맛집 리스트",
            ),
            Task(
                description="맛집 필터링",
                agent=restaurant_filter_agent,
                expected_output="평점 4.0 이상, 리뷰 500개 이상인 후보 리스트",
            ),
            Task(
                description="세부 정보 조회",
                agent=batch_detail_agent,
                expected_output="각 후보 식당의 세부 정보(연락처, 영업시간, 가격대, 웹사이트, 사진, 분류/타입, 비즈니스 상태)를 포함하는 details_map",
            ),
            Task(
                description=(
                    "최종 추천 생성: 필터링된 맛집 후보와 세부 정보를 결합하여, 각 장소는 day_x와 order 필드를 포함해야 합니다. "
                    "day_x는 1부터 시작하여 여행 기간의 각 날짜를 나타내며, order는 0부터 시작하여 각 날짜 내 순서를 나타냅니다. "
                    "최종 출력은 엄격한 JSON 형식이어야 합니다."
                ),
                agent=final_recommendation_agent,
                expected_output="최종 맛집 추천 리스트 (JSON 형식; 각 항목에 day_x, order 필드 포함)",
            ),
        ]

        crew = Crew(
            agents=[
                geocoding_agent,
                restaurant_basic_search_agent,
                restaurant_filter_agent,
                batch_detail_agent,
                final_recommendation_agent,
            ],
            tasks=tasks,
            verbose=True,
        )

        # Crew 실행 (전체 체인 실행)
        crew_result = crew.kickoff()

        # 최종 단계: 별도 세부정보 Task의 결과를 받아 최종 추천 입력에 포함
        # 여기서는 Crew.kickoff() 결과에서 각 Task 결과를 바로 가져올 수 없으므로,
        # 별도로 기본 정보, 필터링 결과, 세부정보를 재수집하는 예시를 사용합니다.
        coord_result = geocoding_agent.tools[0]._run(location)
        basic_result = restaurant_basic_search_agent.tools[0]._run(
            location, coord_result.get("coordinates", "")
        )
        filtered_result = restaurant_filter_agent.tools[0]._run(basic_result)
        place_ids = [
            r.get("place_id", "") for r in filtered_result if r.get("place_id", "")
        ]
        details_map = batch_detail_agent.tools[0]._run(place_ids)
        final_input = {
            "filtered_list": filtered_result,
            "details_map": details_map,
            "travel_plan": travel_plan.dict(),
        }
        final_result = final_recommendation_agent.tools[0]._run(final_input)

        # JSON 직렬화 함수
        def serialize(obj):
            if isinstance(obj, (dict, list, str, int, float, bool, type(None))):
                return obj
            elif hasattr(obj, "dict") and callable(obj.dict):
                return serialize(obj.dict())
            elif hasattr(obj, "__dict__"):
                return {key: serialize(value) for key, value in vars(obj).items()}
            elif isinstance(obj, list):
                return [serialize(item) for item in obj]
            else:
                return str(obj)

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
