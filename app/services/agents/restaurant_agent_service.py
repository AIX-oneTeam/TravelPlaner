import traceback
import os
import requests
import json
from crewai import Agent, Task, Crew, LLM
from datetime import datetime
from dotenv import load_dotenv
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import List, Dict, Type

# 환경 변수 로드
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
GOOGLE_MAP_API_KEY = os.getenv("GOOGLE_MAP_API_KEY")
AGENT_NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
AGENT_NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# 공통 LLM 설정
llm = LLM(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY)


# -------------------------------------------------------------------
# 1. 사용자 여행 데이터 입력 스키마
class Companion(BaseModel):
    label: str
    count: int


class TravelPlan(BaseModel):
    main_location: str
    start_date: str
    end_date: str
    companions: List[Companion]  # 동반자 정보: [{"label": "성인", "count": 3}]
    concepts: List[str]


# 추가: RestaurantSearchTool용 인자 스키마 (기본 정보 용)
class RestaurantSearchArgs(BaseModel):
    location: str
    coordinates: str


# 최종 출력용 스키마
class spot_pydantic(BaseModel):
    kor_name: str = Field(max_length=255)
    eng_name: str = Field(default=None, max_length=255)
    description: str = Field(max_length=255)
    address: str = Field(max_length=255)
    zip: str = Field(max_length=10)
    url: str = Field(default=None, max_length=2083)
    image_url: str = Field(max_length=2083)
    map_url: str = Field(max_length=2083)
    likes: int = None
    satisfaction: float = None
    spot_category: int
    phone_number: str = Field(default=None, max_length=300)
    business_status: bool = None
    business_hours: str = Field(default=None, max_length=255)
    order: int
    day_x: int
    spot_time: str = None


class spots_pydantic(BaseModel):
    spots: List[spot_pydantic]


# -------------------------------------------------------------------
# 2. 좌표 조회 도구 (Google Geocoding API 활용)
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
    backstory="나는 위치 데이터 전문가로, 입력된 location 값을 변경하지 않고 Google Geocoding API를 통해 좌표를 조회한다.",
    tools=[GeocodingTool()],
    llm=llm,
    verbose=True,
)


# -------------------------------------------------------------------
# 3. 맛집 기본 정보 조회 도구 (구글맵에서 title, rating, reviews 포함)
# "place_id" 필드를 제거하고 title, rating, reviews만 반환하도록 수정함.
class RestaurantBasicSearchTool(BaseTool):
    name: str = "RestaurantBasicSearchTool"
    description: str = (
        "주어진 좌표와 location 정보를 기반으로 구글맵에서 식당의 title, rating, reviews를 검색합니다."
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
                    }
                    for r in data.get("local_results", [])
                ]
                all_candidates.extend(candidates)
            except Exception as e:
                print(f"[RestaurantBasicSearchTool] Error at start={start}: {e}")
        return all_candidates


restaurant_basic_search_agent = Agent(
    role="맛집 기본 조회 전문가",
    goal="좌표 정보를 활용하여 식당의 기본 정보(구글맵의 title, rating, reviews)를 조회한다.",
    backstory="나는 맛집 데이터 분석 전문가로, Google Maps API를 사용하여 특정 위치(예: 부산광역시)의 식당 정보를 조회한다.",
    tools=[RestaurantBasicSearchTool()],
    llm=llm,
    verbose=True,
)


# -------------------------------------------------------------------
# 4. 맛집 필터링 도구 (평점 4.0 이상, 리뷰 500개 이상 필터링)
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
    backstory="나는 데이터 필터링 전문가로, 맛집 리뷰와 평점을 분석하여 신뢰할 수 있는 식당 후보를 추려낸다.",
    tools=[RestaurantFilterTool()],
    llm=llm,
    verbose=True,
)


# -------------------------------------------------------------------
# 5-1. 네이버 웹 검색 도구 (텍스트 기반 세부정보 조회)
class NaverWebSearchTool(BaseTool):
    name: str = "NaverWebSearch"
    description: str = (
        "네이버 웹 검색 API를 사용해 식당의 텍스트 기반 세부 정보를 검색합니다."
    )

    def _run(self, query: str) -> str:
        if not AGENT_NAVER_CLIENT_ID or not AGENT_NAVER_CLIENT_SECRET:
            return "[NaverWebSearchTool] 네이버 API 자격 증명이 없습니다."
        url = "https://openapi.naver.com/v1/search/webkr.json"
        headers = {
            "X-Naver-Client-Id": AGENT_NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": AGENT_NAVER_CLIENT_SECRET,
        }
        params = {"query": query, "display": 3, "start": 1, "sort": "random"}
        try:
            resp = requests.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            if not items:
                return f"[NaverWebSearchTool] '{query}' 검색 결과 없음."
            results = []
            for item in items:
                title = item.get("title", "")
                link = item.get("link", "")
                desc = item.get("description", "")
                results.append(f"제목: {title}\n링크: {link}\n설명: {desc}\n")
            return "\n".join(results)
        except Exception as e:
            return f"[NaverWebSearchTool] 에러: {str(e)}"


naver_web_search_agent = Agent(
    role="네이버 웹 검색 에이전트",
    goal="네이버 웹 검색 API를 사용해 식당의 텍스트 기반 세부 정보를 조회한다.",
    backstory="네이버 웹 검색을 통해 식당의 상세 텍스트 정보를 제공합니다.",
    tools=[NaverWebSearchTool()],
    llm=llm,
    verbose=True,
)


# -------------------------------------------------------------------
# 5-2. 네이버 이미지 검색 도구 (이미지 URL 조회)
class NaverImageSearchTool(BaseTool):
    name: str = "NaverImageSearch"
    description: str = (
        "네이버 이미지 검색 API를 사용해 식당에 맞는 이미지 URL을 검색합니다."
    )

    def _run(self, query: str) -> str:
        if not AGENT_NAVER_CLIENT_ID or not AGENT_NAVER_CLIENT_SECRET:
            return "[NaverImageSearchTool] 네이버 API 자격 증명이 없습니다."
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
            if not items:
                return ""
            return items[0].get("link", "")
        except Exception as e:
            return f"[NaverImageSearchTool] 에러: {str(e)}"


naver_image_search_agent = Agent(
    role="네이버 이미지 검색 에이전트",
    goal="네이버 이미지 검색 API를 사용해 식당의 이미지 URL을 조회한다.",
    backstory="네이버 이미지 검색을 통해 식당의 이미지를 제공합니다.",
    tools=[NaverImageSearchTool()],
    llm=llm,
    verbose=True,
)


# -------------------------------------------------------------------
# 6. 최종 추천 생성 도구 (LLM 활용)
# 이 도구는 필터링된 맛집 후보, 네이버 텍스트 기반 세부정보, 그리고 여행 계획(TravelPlan)을 고려하여
# LLM에 최종 추천 리스트 생성을 요청합니다.
class FinalRecommendationTool(BaseTool):
    name: str = "FinalRecommendationTool"
    description: str = (
        "필터링된 맛집 후보, 네이버 텍스트 기반 세부 정보와 여행 계획(TravelPlan)을 고려하여 최종 맛집 추천 리스트를 생성합니다."
    )

    def _run(self, inputs: Dict) -> Dict:
        filtered_list = inputs.get("filtered_list", [])
        text_details_map = inputs.get("text_details_map", {})  # 네이버 텍스트 세부정보
        travel_plan = inputs.get("travel_plan", {})

        # LLM에게 전달할 프롬프트 구성
        prompt = (
            "다음의 필터링된 식당 리스트와 각 식당의 세부정보, 그리고 여행 계획 정보를 고려하여 최종 맛집 추천 리스트를 JSON 형식으로 생성해 주세요.\n"
            '출력 형식은 {"spots": [ ... ]} 이어야 하며, 각 항목은 아래와 같은 정보를 포함해야 합니다:\n'
            "  - kor_name, eng_name, description, address, zip, url, image_url, map_url, likes, satisfaction, spot_category, phone_number, business_status, business_hours, order, day_x, spot_time\n"
            "\n필터링된 식당 리스트:\n"
            f"{filtered_list}\n"
            "\n네이버 텍스트 세부정보 (키는 식당 제목):\n"
            f"{text_details_map}\n"
            "\n여행 계획 정보:\n"
            f"{travel_plan}\n"
            "\n최종 추천 리스트를 JSON 형식으로 출력해 주세요."
        )
        # LLM 호출
        response = self.llm.get_response(prompt)
        try:
            final_output = json.loads(response)
        except Exception as e:
            final_output = {"spots": []}
        return final_output


final_recommendation_agent = Agent(
    role="최종 추천 에이전트",
    goal="필터링된 맛집 후보와 네이버 텍스트 기반 세부 정보를, 여행 계획을 고려하여 최종 맛집 추천 리스트를 생성한다.",
    backstory="나는 데이터 구조화 전문가로, 후보 식당의 기본 정보, 네이버에서 수집한 텍스트 세부 정보와 여행 계획 정보를 종합하여 최종 추천 리스트를 구성한다.",
    tools=[FinalRecommendationTool()],
    llm=llm,
    verbose=True,
    output_pydantic=spots_pydantic,  # 최종 출력 스키마 연결
)


# -------------------------------------------------------------------
# 7. 최종 추천 사진 업데이트 도구
# 이 도구는 최종 추천 리스트에 포함된 각 맛집에 대해 네이버 이미지 검색 API를 호출하여 이미지 URL을 추가합니다.
class FinalImageUpdateTool(BaseTool):
    name: str = "FinalImageUpdateTool"
    description: str = (
        "최종 추천 리스트에 포함된 맛집에 대해 네이버 이미지 검색 API를 사용해 이미지 URL을 업데이트합니다."
    )

    def _run(self, final_data: Dict) -> Dict:
        spots = final_data.get("spots", [])
        for spot in spots:
            query = spot.get("kor_name", "")
            if query:
                image_url = naver_image_search_agent.tools[0]._run(query)
                spot["image_url"] = image_url
        return {"spots": spots}


final_image_update_agent = Agent(
    role="최종 이미지 업데이트 에이전트",
    goal="최종 추천 리스트에 포함된 맛집에 대해 네이버 이미지 검색 API를 통해 이미지 URL을 업데이트한다.",
    backstory="나는 최종 추천 리스트의 맛집들에 대해, 네이버 이미지 검색을 통해 적절한 이미지 URL을 찾아 업데이트하는 역할을 맡는다.",
    tools=[FinalImageUpdateTool()],
    llm=llm,
    verbose=True,
)


# -------------------------------------------------------------------
# 8. 전체 Crew 구성 및 실행 함수
def create_recommendation(input_data: dict) -> dict:
    try:
        travel_plan = TravelPlan(**input_data)
        location = travel_plan.main_location

        # Task 구성 – 각 태스크에 해당 에이전트를 지정
        tasks = [
            Task(
                description="좌표 조회",
                agent=geocoding_agent,
                expected_output="{'location': '부산광역시', 'coordinates': '...'}",
            ),
            Task(
                description="맛집 기본 조회",
                agent=restaurant_basic_search_agent,
                expected_output="구글맵에서 title, rating, reviews를 포함한 맛집 리스트",
            ),
            Task(
                description="맛집 필터링",
                agent=restaurant_filter_agent,
                expected_output="평점 4.0 이상, 리뷰 500개 이상인 후보 리스트",
            ),
            Task(
                description="세부 정보 조회 (네이버 텍스트)",
                agent=naver_web_search_agent,
                expected_output="각 후보 식당의 네이버 웹 검색 텍스트 세부 정보 결과",
            ),
            Task(
                description="최종 추천 생성",
                agent=final_recommendation_agent,
                expected_output="최종 맛집 추천 리스트 (JSON 형식; spots_pydantic에 맞게)",
            ),
            Task(
                description="최종 추천 사진 업데이트",
                agent=final_image_update_agent,
                expected_output="최종 맛집 추천 리스트의 각 항목에 네이버 이미지 URL이 추가된 결과",
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
                final_image_update_agent,
            ],
            tasks=tasks,
            verbose=True,
        )

        # Crew 실행 (전체 체인 실행)
        crew_result = crew.kickoff()

        # 최종 단계: 각 단계별 결과 재수집
        # 1. 좌표 조회
        coord_result = geocoding_agent.tools[0]._run(location)
        # 2. 맛집 기본 조회 (구글맵)
        basic_result = restaurant_basic_search_agent.tools[0]._run(
            location, coord_result.get("coordinates", "")
        )
        # 3. 맛집 필터링
        filtered_result = restaurant_filter_agent.tools[0]._run(basic_result)

        # 4. 네이버 텍스트 세부정보 조회: 각 후보의 'title'을 기준으로 네이버 웹 검색 텍스트 결과 수집
        text_details_map = {}
        for restaurant in filtered_result:
            restaurant_name = restaurant.get("title", "")
            if restaurant_name:
                text_info = naver_web_search_agent.tools[0]._run(restaurant_name)
                text_details_map[restaurant_name] = text_info

        # 5. 최종 추천 생성: 필터링 결과, 네이버 텍스트 세부정보, 여행 계획을 결합하여 최종 추천 리스트 생성
        final_input = {
            "filtered_list": filtered_result,
            "text_details_map": text_details_map,
            "travel_plan": travel_plan.dict(),
        }
        final_recommendation = final_recommendation_agent.tools[0]._run(final_input)

        # 6. 최종 추천 사진 업데이트: 최종 추천 리스트에 대해 네이버 이미지 검색으로 이미지 URL 추가
        final_result = final_image_update_agent.tools[0]._run(final_recommendation)

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
        "companions": [{"label": "성인", "count": 2}, {"label": "어린이", "count": 1}],
        "concepts": ["가족", "맛집"],
        "name": "부산 여행 일정",
    }
    result = create_recommendation(test_input)
    print(json.dumps(result, ensure_ascii=False, indent=2))
