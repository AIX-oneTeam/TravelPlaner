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
    ages: str
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
            "query": f"{query} 맛집 리뷰",  # 검색어 최적화
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
            "query": f"{query} 맛집 대표메뉴",  # 검색어 최적화
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


# class FinalRecommendationTool(BaseTool):
#     name: str = "FinalRecommendationTool"
#     description: str = (
#         "필터링된 맛집 후보와 상세 정보를 결합하여 최종 추천 리스트를 생성합니다."
#     )

#     def _run(self, inputs: Dict) -> Dict:
#         try:
#             filtered_list = inputs.get("filtered_list", [])
#             text_details = inputs.get("text_details", {})
#             image_urls = inputs.get("image_urls", {})
#             travel_plan = inputs.get("travel_plan", {})

#             # 날짜 처리 예외 처리 추가
#             start_date = travel_plan.get("start_date")
#             end_date = travel_plan.get("end_date")

#             if not start_date or not end_date:
#                 raise ValueError("여행 날짜 정보가 누락되었습니다.")

#             start_date = datetime.strptime(start_date, "%Y-%m-%d")
#             end_date = datetime.strptime(end_date, "%Y-%m-%d")
#             total_days = (end_date - start_date).days + 1

#             spots = []
#             day_x = 1
#             order = 1

#             for restaurant in filtered_list:
#                 name = restaurant.get("title", "")
#                 details = text_details.get(name, {})

#                 # 시간대별 방문 시간 설정
#                 spot_time = (
#                     "08:00 AM"
#                     if order == 1
#                     else "12:00 PM" if order == 2 else "07:00 PM"
#                 )

#                 spot = spot_pydantic(
#                     kor_name=name,
#                     eng_name=details.get("eng_name"),
#                     description=details.get("description", "정보 없음"),
#                     address=details.get("address", "주소 없음"),
#                     latitude=restaurant.get("latitude", 0.0),
#                     longitude=restaurant.get("longitude", 0.0),
#                     url=details.get("url"),
#                     image_url=image_urls.get(name, ""),
#                     map_url=f"https://maps.google.com/?q={restaurant.get('latitude', 0.0)},{restaurant.get('longitude', 0.0)}",
#                     spot_category=2,
#                     phone_number=details.get("phone_number"),
#                     business_status=details.get("business_status", True),
#                     business_hours=details.get("business_hours"),
#                     order=order,
#                     day_x=day_x,
#                     spot_time=spot_time,
#                 )
#                 spots.append(spot)

#                 if order == 3:
#                     order = 1
#                     day_x += 1
#                     if day_x > total_days:
#                         break
#                 else:
#                     order += 1

#             return {"spots": spots}

#         except Exception as e:
#             print(f"FinalRecommendationTool 오류: {str(e)}")
#             raise


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
    role="웹 검색 에이전트",
    goal="네이버 웹 검색 API를 사용해 식당의 텍스트 기반 세부 정보를 조회한다.",
    backstory="""저는 정보 분석가로서 네이버 웹 검색을 활용하여 각 식당의 상세 텍스트 정보를 체계적으로 수집합니다. 신뢰할 수 있는 데이터를 제공함으로써, 사용자의 여행 경험을 극대화합니다.""",
    tools=[NaverWebSearchTool()],
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

# 네이버 이미지 검색 에이전트
naver_image_search_agent = Agent(
    role="이미지 검색 전문가",
    goal="네이버 이미지 검색 API를 사용해 식당의 이미지 URL을 조회한다.",
    backstory="""저는 이미지 수집가로서 네이버 이미지 검색을 통해 각 식당의 고품질 이미지를 수집합니다.""",
    tools=[NaverImageSearchTool()],
    llm=llm,
    verbose=True,
)


# ------------------------- Task & Crew ------------------------------
def create_recommendation(input_data: dict) -> dict:
    try:
        travel_plan = TravelPlan(**input_data)
        print(f"[DEBUG3] input_data: {input_data}")

        # Task 정의
        tasks = [
            Task(
                description=f"""{travel_plan.main_location}의 좌표 조회""",
                agent=geocoding_agent,
                expected_output="위치 좌표",
                context={"location": travel_plan.main_location},
            ),
            Task(
                description="""맛집 기본 정보 조회""",
                agent=restaurant_basic_search_agent,
                expected_output="맛집 기본 정보 리스트",
                context={
                    "geocoding_result": "$prev_task_0"  # 첫 번째 태스크의 결과 참조
                },
            ),
            Task(
                description="""맛집 필터링 (평점 4.0 이상, 리뷰 500개 이상)""",
                agent=restaurant_filter_agent,
                expected_output="필터링된 맛집 리스트",
                config={},
            ),
            Task(
                description="""세부 정보 조회""",
                agent=naver_web_search_agent,
                expected_output="각 후보 식당의 세부 정보(연락처, 영업시간, 가격대, 웹사이트, 사진, 분류/타입, 비즈니스 상태)를 포함하는 details_map",
            ),
            Task(
                description=f"""이전 단계에서 수집한 {travel_plan.main_location} 지역의 맛집 데이터를 바탕으로, {travel_plan.start_date}부터 {travel_plan.end_date}까지 여행하는 {travel_plan.ages} 연령대의 고객과 동반자({', '.join([f'{c.label} {c.count}명' for c in travel_plan.companions])})의 {', '.join(travel_plan.concepts)} 컨셉에 맞는 최종 맛집 리스트를 추천하라.
                최종 추천 과정에서는 다음 사항을 반드시 반영할 것:
                1. 수집된 데이터를 활용하여, 사용자 여행 일정, 동선, 연령대, 동반자 정보, 그리고 여행 컨셉에 최적화된 맛집 리스트를 구성한다.
                2. 각 맛집의 최신 정보(주소, 설명, 전화번호, 영업 상태 등)를 네이버 웹 검색 결과를 통해 확인하고 검증한다.
                3. 추천된 맛집 정보는 아래 JSON 객체 형식을 엄격하게 준수하여 반환해야 하며, 형식에 맞지 않거나 불필요한 부가 텍스트가 포함되어서는 안 된다.
                {{
                "kor_name": "string",
                "eng_name": "string",
                "description": "string",
                "address": "string",
                "url": "string",
                "image_url": "string",
                "map_url": "string",
                "latitude": "float",
                "longitude": "float",
                "spot_category": 2,
                "phone_number": "string",
                "business_status": true,
                "business_hours": "string",
                "order": int,
                "day_x": int,
                "spot_time": "string"
                }}
                - 각 장소는 day_x, order 필드로 일정에 포함될 날짜와 순서를 지정한다.
                - day_x는 반드시 1부터 시작하여 증가하는 숫자이며, 여행 기간의 각각의 날짜를 의미한다.
                - order는 반드시 1부터 시작하여 증가하는 숫자이며, 각 날짜 내에서 장소의 방문 순서를 의미한다.
                - spot_time 형식은 '%H:%M:%S' 형식의 문자열로 변환한다.""",
                agent=final_recommendation_agent,
                expected_output="최종 추천 맛집 리스트",
                output_pydantic=spots_pydantic,
                config={
                    "travel_plan": travel_plan.dict(),
                    "previous_results": "이전 태스크 결과",
                },
            ),
            Task(
                description=f"""[이미지 삽입]
                - CrewAI가 생성한 여행 일정 pydantic 형식에서 각 장소의 `kor_name`을 기반으로 이미지를 검색한다.
                - 검색된 이미지는 해당 장소의 `image_url` 필드에 추가한다.
                - 각 장소 정보를 spot_request 형식으로 변환한다.
                - 모든 장소는 기간 구분 없이 단일 리스트인 `spots`에 포함시킨다.""",
                agent=naver_image_search_agent,
                expected_output="pydantic 형식의 여행 일정 데이터",
                output_pydantic=spots_pydantic,
                config={},
            ),
        ]

        crew = Crew(
            tasks=tasks,
            agents=[
                geocoding_agent,
                restaurant_basic_search_agent,
                restaurant_filter_agent,
                naver_web_search_agent,
                final_recommendation_agent,
                naver_image_search_agent,
            ],
            verbose=True,
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
