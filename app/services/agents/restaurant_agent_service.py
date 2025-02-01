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
    backstory="나는 위치 데이터 전문가이며, 구글 Geocoding API를 활용해 정확한 좌표를 제공할 수 있다.",
    tools=[GeocodingTool()],
    llm=LLM(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY),
    verbose=True,
)


# -------------------------------------------------------------------
# 3. 맛집 후보 조회 툴 (serpAPI 기반)
class RestaurantSearchTool(BaseTool):
    name: str = "RestaurantSearchTool"
    description: str = (
        "주어진 좌표 정보를 바탕으로 serpAPI의 구글맵 API를 호출해 맛집 후보 리스트를 최대 40개(20개씩 2회) 조회합니다."
    )
    # 수정: TravelPlan 대신 RestaurantSearchArgs 사용
    args_schema: Type[BaseModel] = RestaurantSearchArgs

    def __init__(self, serpapi_key: str, google_maps_api_key: str):
        super().__init__()
        self._serpapi_key = serpapi_key
        self._google_maps_api_key = google_maps_api_key

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
                "api_key": self._serpapi_key,
                "start": start,
            }
            try:
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                candidates = data.get("local_results", [])
                all_candidates.extend(candidates)
            except Exception as e:
                print(f"[RestaurantSearchTool] Error at start={start}: {e}")
        return all_candidates


# 맛집 후보 조회 에이전트 생성
restaurant_search_agent = Agent(
    role="맛집 조회 전문가",
    goal="좌표 정보를 활용하여 맛집 후보 리스트(최대 40개)를 조회한다.",
    backstory="나는 맛집 검색 전문가이며, serpAPI를 통해 후보 리스트를 제공할 수 있다.",
    tools=[RestaurantSearchTool(SERPAPI_API_KEY, GOOGLE_MAP_API_KEY)],
    llm=LLM(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY),
    verbose=True,
)


# -------------------------------------------------------------------
# 4. 맛집 후보 필터링 툴
class RestaurantFilterTool(BaseTool):
    name: str = "RestaurantFilterTool"
    description: str = (
        "조회된 맛집 후보 리스트 중 평점 4점 이상, 리뷰 수 500개 이상인 식당만 필터링합니다."
    )

    def _run(self, candidates: List[Dict]) -> List[Dict]:
        filtered = []
        seen = set()
        for result in candidates:
            try:
                rating = float(result.get("rating", 0))
                reviews = int(result.get("reviews", 0))
            except Exception:
                continue
            unique_key = f"{result.get('title', '')}_{result.get('address', '')}"
            if rating >= 4.0 and reviews >= 500 and unique_key not in seen:
                restaurant = {
                    "kor_name": result.get("title", ""),
                    "eng_name": result.get("title", "")
                    .encode("ascii", "ignore")
                    .decode(),
                    "description": "",
                    "address": result.get("address", ""),
                    "zip": "",
                    "url": result.get("website", ""),
                    "image_url": result.get("thumbnail", ""),
                    "map_url": f"https://www.google.com/maps/place/?q=place_id:{result.get('place_id')}",
                    "likes": reviews,
                    "satisfaction": rating,
                    "spot_category": 1,
                    "phone_number": result.get("phone", ""),
                    "business_status": True,
                    "business_hours": result.get("hours", ""),
                }
                filtered.append(restaurant)
                seen.add(unique_key)
        return filtered


# 맛집 필터링 에이전트 생성
restaurant_filter_agent = Agent(
    role="맛집 필터링 전문가",
    goal="맛집 후보 리스트 중 조건에 맞는 식당만을 선별한다.",
    backstory="나는 데이터 필터링 전문가로, 후보 리스트에서 평점과 리뷰 수 기준으로 유효한 식당을 선별할 수 있다.",
    tools=[RestaurantFilterTool()],
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

    def _run(self, filtered_list: str) -> str:
        # filtered_list가 리스트라면 문자열로 변환합니다.
        if isinstance(filtered_list, list):
            filtered_list = json.dumps(filtered_list, ensure_ascii=False)

        system_prompt = """당신은 여행객들을 위한 맛집 추천 전문가이자, JSON 생성기입니다.
절대로 JSON 형식 이외의 텍스트를 출력하지 마세요. 
특히 "안녕하세요", "추천 리스트는 다음과 같습니다" 같은 문구는 절대 넣지 말고, 
오직 아래 형식의 JSON 하나만 결과로 내놓으세요.

1박 2일 여행이면 총 2일이므로, 하루에 3곳씩(아침, 점심, 저녁) 해서 총 6곳을 선정해야 합니다.
만약 후보가 6곳 미만이라면 나머지를 "적합한 후보가 부족합니다" 등으로 처리하세요.

아래 형식에 맞춰서 반드시 출력해야 합니다 (JSON 시작 전후로 추가 문구 금지):

{
  "Spots": [
    {
      "kor_name": "string",
      "eng_name": "string",
      "description": "string",
      "address": "string",
      "zip": "string",
      "url": "string",
      "image_url": "string",
      "map_url": "string",
      "likes": 0,
      "satisfaction": 0,
      "spot_category": 0,
      "phone_number": "string",
      "business_status": true,
      "business_hours": "string",
      "day_x": 0,
      "order": 0,
      "spot_time": "2025-02-01T09:00:00"
    }
  ]
}

- Spots 배열의 길이는 6이어야 합니다(2일 × 3곳).
- day_x: 1 또는 2
- order: 1, 2, 3
- spot_time: ISO 8601 형식 "YYYY-MM-DDTHH:mm:ss"
- 반드시 RestaurantSearchTool로부터 받은 후보 중에서만 골라야 합니다.
- 후보가 6개 미만이라면 남은 객체들을 "reason": "적합한 후보가 부족합니다" 같은 식으로 설명을 넣으세요 (그러나 JSON 필드는 위와 동일하게 유지).

예시 여행 계획:
- main_location: 부산광역시
- start_date: 2025-02-01T00:00:00
- end_date: 2025-02-02T00:00:00
- companion_count: 3
- concepts: ['가족', '맛집']

이 모든 조건을 지키지 않으면 잘못된 답변입니다. 오직 JSON만 정확히 출력하세요.
"""
        prompt = f"{system_prompt}\n\n맛집 후보 리스트:\n{filtered_list}"
        # 실제로는 LLM 호출을 통해 결과를 받아야 하지만, 여기서는 프롬프트를 반환 예시로 사용
        return prompt.strip()


# 최종 추천 생성 에이전트 생성
final_recommendation_agent = Agent(
    role="최종 추천 에이전트",
    goal="필터링된 맛집 후보 리스트를 바탕으로 최종 추천 맛집 리스트를 엄격한 JSON 형식으로 생성한다.",
    backstory="나는 여행객들을 위한 맛집 추천 전문가이자 JSON 생성기입니다. 오직 JSON 형식만 출력해야 합니다.",
    tools=[FinalRecommendationTool()],
    llm=LLM(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY),
    verbose=True,
)


# -------------------------------------------------------------------
# 6. 전체 Crew 구성 및 실행 함수
def create_recommendation(input_data: dict) -> dict:
    try:
        # 사용자 여행 데이터 처리
        travel_plan = TravelPlan(**input_data)
        location = travel_plan.main_location

        # 태스크 1: 좌표 조회
        geocoding_task = Task(
            description=f"[좌표 조회]\n'{location}'의 위도와 경도를 조회합니다.",
            agent=geocoding_agent,
            expected_output="위도,경도 형식의 문자열",
        )

        # 태스크 2: 맛집 후보 조회 (좌표 필요)
        restaurant_search_task = Task(
            description=f"[맛집 조회]\n'{location}'의 맛집 후보 리스트를 조회합니다.",
            agent=restaurant_search_agent,
            context=[geocoding_task],
            expected_output="맛집 후보 리스트 (원시 데이터)",
        )

        # 태스크 3: 맛집 후보 필터링
        restaurant_filter_task = Task(
            description="[맛집 필터링]\n조회된 맛집 후보 리스트 중 평점 4점 이상, 리뷰 500개 이상인 식당만 선별합니다.",
            agent=restaurant_filter_agent,
            context=[restaurant_search_task],
            expected_output="필터링된 맛집 리스트 (리스트 형식)",
        )

        # 태스크 4: 최종 추천 생성 (엄격한 JSON 형식)
        final_recommendation_task = Task(
            description="[최종 추천 생성]\n필터링된 맛집 리스트를 참고하여, 지정된 프롬프트에 따라 최종 추천 맛집 리스트를 JSON 형식으로 출력합니다.",
            agent=final_recommendation_agent,
            context=[restaurant_filter_task],
            expected_output="엄격한 JSON 형식의 추천 맛집 리스트",
        )

        # Crew 구성: 모든 태스크 등록
        crew = Crew(
            agents=[
                geocoding_agent,
                restaurant_search_agent,
                restaurant_filter_agent,
                final_recommendation_agent,
            ],
            tasks=[
                geocoding_task,
                restaurant_search_task,
                restaurant_filter_task,
                final_recommendation_task,
            ],
            verbose=True,
        )

        final_result = crew.kickoff()

        # 최종 결과가 JSON 형식인지 확인 후 반환 (예: 최종 결과에 Spots 필드가 있으면)
        if hasattr(final_result, "Spots"):
            result_json = {"Spots": final_result.Spots}
        else:
            result_json = final_result

        return {
            "message": "요청이 성공적으로 처리되었습니다.",
            "plan": {
                "name": input_data.get("name", "여행 일정"),
                "start_date": input_data["start_date"],
                "end_date": input_data["end_date"],
                "main_location": location,
                "companion_count": travel_plan.companion_count,
                "concepts": ", ".join(travel_plan.concepts),
                "created_at": datetime.now().strftime("%Y-%m-%d"),
                "updated_at": datetime.now().strftime("%Y-%m-%d"),
            },
            "spots": result_json if isinstance(result_json, list) else [],
        }
    except Exception as e:
        print(f"[ERROR] {e}")
        traceback.print_exc()
        return {"message": "요청 처리 중 오류가 발생했습니다.", "error": str(e)}


# -------------------------------------------------------------------
# 예시 실행 (테스트)
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
