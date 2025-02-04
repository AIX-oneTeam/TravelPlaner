import traceback
import os
import requests
import json
from fastapi import FastAPI, HTTPException
from crewai import Agent, Task, Crew, LLM
from datetime import datetime
from dotenv import load_dotenv
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import List, Dict, Type

app = FastAPI()

# 환경 변수 로드
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
GOOGLE_MAP_API_KEY = os.getenv("GOOGLE_MAP_API_KEY")
AGENT_NAVER_CLIENT_ID = os.getenv("AGENT_NAVER_CLIENT_ID")
AGENT_NAVER_CLIENT_SECRET = os.getenv("AGENT_NAVER_CLIENT_SECRET")

llm = LLM(model="gpt-3.5-turbo", temperature=0, api_key=OPENAI_API_KEY)


# 1. 사용자 여행 데이터 입력 스키마
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


# ------------------------- Tool ------------------------------
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


# 3. 맛집 기본 정보 조회 도구 (title, rating, reviews)
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


# 4. 맛집 필터링 도구 (평점 4.0 이상, 리뷰 500개 이상 필터링)
class RestaurantFilterTool(BaseTool):
    name: str = "RestaurantFilterTool"
    description: str = (
        "조회된 맛집 리스트 중 평점 4.0 이상, 리뷰 500개 이상인 식당만 필터링합니다."
    )

    def _run(self, candidates: List[Dict]) -> List[Dict]:
        """필터링된 맛집 리스트 반환"""
        filtered_list = [
            r
            for r in candidates
            if r.get("rating", 0) >= 4.0 and r.get("reviews", 0) >= 500
        ]
        print(f"필터링된 맛집 개수: {len(filtered_list)}")
        return filtered_list


# 5-1. 네이버 웹 검색 도구 (텍스트 기반 세부정보 조회)
class NaverWebSearchTool(BaseTool):
    name: str = "NaverWebSearch"
    description: str = (
        "네이버 웹 검색 API를 사용해 식당의 텍스트 기반 세부 정보를 검색합니다."
    )

    def _run(self, queries: List[str]) -> Dict[str, List[spot_pydantic]]:
        """여러 가게에 대한 네이버 검색 결과를 `spot_pydantic` 형식으로 반환"""
        if not isinstance(queries, list):
            raise ValueError(
                f"`queries`는 `List[str]` 형식이어야 합니다. 현재: {type(queries)}"
            )
        if not AGENT_NAVER_CLIENT_ID or not AGENT_NAVER_CLIENT_SECRET:
            return {"error": "[NaverWebSearchTool] 네이버 API 자격 증명이 없습니다."}
        url = "https://openapi.naver.com/v1/search/webkr.json"
        headers = {
            "X-Naver-Client-Id": AGENT_NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": AGENT_NAVER_CLIENT_SECRET,
        }
        results = {"spots": []}
        for query in queries:
            params = {"query": query, "display": 3, "start": 1, "sort": "random"}
            try:
                resp = requests.get(url, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()
                items = data.get("items", [])
                web_result = {
                    "kor_name": query,
                    "description": (
                        items[0].get("description", "설명 없음")
                        if items
                        else "설명 없음"
                    ),
                    "url": items[0].get("link", "") if items else "",
                }
                results["spots"].append(spot_pydantic(**web_result).dict())
            except Exception as e:
                results["spots"].append(
                    {"kor_name": query, "error": f"[NaverWebSearchTool] 에러: {str(e)}"}
                )
        return results


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
            return items[0].get("link", "") if items else ""
        except Exception as e:
            return f"[NaverImageSearchTool] 에러: {str(e)}"


# 6. 최종 추천 생성 도구(prompt 사용)
class FinalRecommendationTool(BaseTool):
    name: str = "FinalRecommendationTool"
    description: str = (
        "필터링된 맛집 후보, 네이버 텍스트 기반 세부 정보와 여행 계획(TravelPlan)을 고려하여 최종 맛집 추천 리스트를 생성합니다."
    )

    def __init__(self, llm: LLM):
        super().__init__()
        self.llm = llm

    def _run(self, inputs: Dict) -> Dict:
        filtered_list = inputs.get("filtered_list", [])
        text_details_map = inputs.get("text_details_map", {})  # 네이버 텍스트 세부정보
        travel_plan = inputs.get("travel_plan", {})

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

        response = self.llm.get_response(prompt)
        try:
            final_output = json.loads(response)
        except Exception as e:
            final_output = {"spots": []}
        return final_output

# 6. 최종 추천 생성 도구(prompt 사용)
class FinalRecommendationTool(BaseTool):
    name: str = "FinalRecommendationTool"
    description: str = (
        "필터링된 맛집 후보, 네이버 텍스트 기반 세부 정보와 여행 계획(TravelPlan)을 고려하여 최종 맛집 추천 리스트를 생성합니다."
    )

    def _run(self, inputs: Dict) -> Dict:
        filtered_list = inputs.get("filtered_list", [])
        text_details_map = inputs.get("text_details_map", {})  # 네이버 텍스트 세부정보
        travel_plan = inputs.get("travel_plan", {})

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

        response = self.llm.get_response(prompt)
        try:
            final_output = json.loads(response)
        except Exception as e:
            final_output = {"spots": []}
        return final_output

# ------------------------- Agent ------------------------------
# 좌표 조회
geocoding_agent = Agent(
    role="좌표 조회 전문가",
    goal="사용자가 입력한 location의 위도와 경도를 조회.",
    backstory="나는 위치 데이터 전문가로, 사용자가 입력한 장소의 좌표를 정확하게 찾아 제공한다.",
    tools=[GeocodingTool()],
    llm=llm,
    verbose=True,
)

# 맛집 조회
restaurant_basic_search_agent = Agent(
    role="맛집 기본 조회 전문가",
    goal="좌표 정보를 활용하여 구글맵에서 맛집 기본 정보를 조회.",
    backstory="나는 맛집 데이터 분석 전문가로, 구글맵 데이터를 활용하여 정확한 맛집 정보를 제공한다.",
    tools=[RestaurantBasicSearchTool()],
    llm=llm,
    verbose=True,
)

# 맛집 필터링
restaurant_filter_agent = Agent(
    role="맛집 필터링 전문가",
    goal="평점과 리뷰 수 기준으로 식당 후보를 선별한다.",
    backstory="나는 데이터 필터링 전문가로, 리뷰와 평점을 분석하여 신뢰할 수 있는 식당 후보를 추려낸다.",
    tools=[RestaurantFilterTool()],
    llm=llm,
    verbose=True,
)

# 네이버 웹 검색
naver_web_search_agent = Agent(
    role="네이버 웹 검색 에이전트",
    goal="필터링된 식당 리스트를 받아 네이버 웹 검색을 수행.",
    backstory="나는 네이버 웹 검색 전문가로, 식당과 관련된 다양한 텍스트 기반 정보를 검색하여 제공한다.",
    tools=[NaverWebSearchTool()],
    llm=llm,
    verbose=True,
    output_pydantic=spots_pydantic,
)

# 네이버 이미지 검색
naver_image_search_agent = Agent(
    role="네이버 이미지 검색 에이전트",
    goal="필터링된 식당 리스트를 받아 네이버 이미지 검색을 수행.",
    backstory="나는 이미지 검색 전문가로, 네이버 이미지 검색을 활용하여 식당의 대표 이미지를 제공한다.",
    tools=[NaverImageSearchTool()],
    llm=llm,
    verbose=True,
    output_pydantic=spots_pydantic,
)

# 최종 추천 생성
final_recommendation_agent = Agent(
    role="최종 추천 에이전트",
    goal="사용자 여행 일정과 필터링된 맛집 정보를 조합하여 최종 추천 리스트를 생성.",
    backstory="나는 데이터 분석 및 추천 전문가로, 사용자 여행 일정과 맛집 데이터를 활용해 최적의 맛집 추천 리스트를 제공한다.",
    tools=[FinalRecommendationTool(llm)],
    llm=llm,
    verbose=True,
    output_pydantic=spots_pydantic,
)


# 8. 전체 Crew 구성 및 실행 함수
def create_recommendation(input_data: dict) -> dict:
    try:
        travel_plan = TravelPlan(**input_data)

        tasks = [
            Task(
                description="좌표 조회",
                agent=geocoding_agent,
                expected_output={"location": "부산광역시", "coordinates": "..."},
            ),
            Task(
                description="맛집 기본 조회",
                agent=restaurant_basic_search_agent,
                expected_output=[{"title": "식당1", "rating": 4.2, "reviews": 7262}],
                context=["좌표 조회"],
            ),
            Task(
                description="맛집 필터링",
                agent=restaurant_filter_agent,
                expected_output=[{"title": "식당1", "rating": 4.5, "reviews": 1000}],
                context=["맛집 기본 조회"],
            ),
            Task(
                description="네이버 웹 검색 실행",
                agent=naver_web_search_agent,
                expected_output=[
                    {"kor_name": "식당1", "description": "이곳은 유명한 맛집입니다."}
                ],
                context=["맛집 필터링"],
            ),
            Task(
                description="네이버 이미지 검색 실행",
                agent=naver_image_search_agent,
                expected_output=[
                    {"kor_name": "식당1", "image_url": "https://example.com"}
                ],
                context=["맛집 필터링"],
            ),
            Task(
                description="최종 추천 생성",
                agent=final_recommendation_agent,
                expected_output={
                    "spots": [
                        {
                            "kor_name": "식당1",
                            "description": "이곳은 유명한 맛집입니다.",
                            "image_url": "https://example.com",
                        }
                    ]
                },
                context=[
                    "네이버 웹 검색 실행",
                    "네이버 이미지 검색 실행",
                ],
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
        print(f"[ERROR] {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

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
