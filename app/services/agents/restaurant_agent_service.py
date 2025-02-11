import traceback
import os
import json
import asyncio
import aiohttp
from datetime import datetime
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, LLM
from crewai.tools import BaseTool
from typing import List, Dict, Optional
from fastapi import HTTPException
from app.dtos.spot_models import spots_pydantic

# 환경 변수 로드
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_MAP_API_KEY = os.getenv("GOOGLE_MAP_API_KEY")
AGENT_NAVER_CLIENT_ID = os.getenv("AGENT_NAVER_CLIENT_ID")
AGENT_NAVER_CLIENT_SECRET = os.getenv("AGENT_NAVER_CLIENT_SECRET")

llm = LLM(model="gpt-4o", temperature=0, api_key=OPENAI_API_KEY)

# ------------------------- 비동기 Tool 클래스 -------------------------
# 1. Google Geocoding API를 사용하여 좌표를 조회하는 Tool
class GeocodingTool(BaseTool):
    name: str = "GeocodingTool"
    description: str = (
        "Google Geocoding API를 사용하여 주어진 위치의 위도와 경도를 조회합니다. "
        "입력된 location 값은 변경 없이 그대로 반환합니다."
    )

    async def _arun(self, location: str) -> Dict:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": location, "key": GOOGLE_MAP_API_KEY}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    if data.get("results"):
                        loc = data["results"][0]["geometry"]["location"]
                        coordinates = f"{loc['lat']},{loc['lng']}"
                    else:
                        coordinates = ""
        except Exception as e:
            coordinates = f"[GeocodingTool] Error: {str(e)}"
        return {"location": location, "coordinates": coordinates}

    def _run(self, location: str) -> Dict:
        return asyncio.run(self._arun(location))


# 2. Google Places API를 사용해 맛집 기본 정보를 조회하는 Tool
class RestaurantBasicSearchTool(BaseTool):
    name: str = "RestaurantBasicSearchTool"
    description: str = (
        "주어진 좌표와 location 정보를 기반으로 구글맵에서 식당의 title, rating, reviews를 검색합니다."
    )

    async def get_place_details(
        self, session: aiohttp.ClientSession, place_id: str
    ) -> Dict:
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "fields": "name,rating,user_ratings_total,geometry",
            "language": "ko",
            "key": GOOGLE_MAP_API_KEY,
        }
        try:
            async with session.get(url, params=params) as response:
                data = await response.json()
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

    async def _arun(self, location: str, coordinates: str) -> List[Dict]:
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
            async with aiohttp.ClientSession() as session:
                # 첫 번째 요청
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    print(f"첫 요청 결과 수: {len(data.get('results', []))}")
                    for place in data.get("results", []):
                        place_id = place.get("place_id")
                        if place_id:
                            details = await self.get_place_details(session, place_id)
                            if (
                                details
                                and details["rating"] >= 4.0
                                and details["reviews"] >= 500
                            ):
                                all_candidates.append(details)
                    next_page_token = data.get("next_page_token")

                # 추가 요청: 후보 수가 10개 미만이면 추가로 요청
                while next_page_token and len(all_candidates) < 15:
                    try:
                        await asyncio.sleep(3)  # next_page_token 유효 대기
                        params["pagetoken"] = next_page_token
                        async with session.get(url, params=params) as response:
                            data = await response.json()
                            new_results = data.get("results", [])
                            print(f"추가 요청 결과 수: {len(new_results)}")
                            for place in new_results:
                                # 상한선(예: 40개)은 기존 코드와 동일하게 유지
                                if len(all_candidates) >= 40:
                                    break
                                place_id = place.get("place_id")
                                if place_id:
                                    details = await self.get_place_details(
                                        session, place_id
                                    )
                                    if (
                                        details
                                        and details["rating"] >= 4.0
                                        and details["reviews"] >= 500
                                    ):
                                        all_candidates.append(details)
                            next_page_token = data.get("next_page_token")
                    except Exception as e:
                        print(f"추가 페이지 요청 오류: {e}")
                        break

                print(f"최종 수집된 맛집 수: {len(all_candidates)}")
        except Exception as e:
            print(f"[RestaurantBasicSearchTool] Search Error: {e}")
        return all_candidates

    def _run(self, location: str, coordinates: str) -> List[Dict]:
        return asyncio.run(self._arun(location, coordinates))


# 3. 네이버 웹 검색 API를 사용해 식당의 세부 정보를 조회하는 Tool
class NaverWebSearchTool(BaseTool):
    name: str = "NaverWebSearch"
    description: str = "네이버 웹 검색 API를 사용해 식당의 상세 정보를 검색합니다."

    async def fetch(self, session: aiohttp.ClientSession, query: str):
        url = "https://openapi.naver.com/v1/search/webkr.json"
        headers = {
            "X-Naver-Client-Id": AGENT_NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": AGENT_NAVER_CLIENT_SECRET,
        }
        print(f"[네이버 세부정부 검색어]: {query}")
        params = {
            "query": query,
            "display": 3,
            "start": 1,
            "sort": "sim",
        }
        try:
            async with session.get(url, headers=headers, params=params) as response:
                data = await response.json()
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

    async def _arun(self, restaurant_list: List[str]) -> Dict[str, Dict[str, str]]:
        results = {}
        async with aiohttp.ClientSession() as session:
            for restaurant in restaurant_list:
                results[restaurant] = await self.fetch(session, restaurant)
        return results

    def _run(self, restaurant_list: List[str]) -> Dict[str, Dict[str, str]]:
        return asyncio.run(self._arun(restaurant_list))


# 4. 네이버 이미지 검색 API를 사용해 식당의 대표 이미지를 조회하는 Tool
class NaverImageSearchTool(BaseTool):
    name: str = "NaverImageSearch"
    description: str = (
        "네이버 이미지 검색 API를 사용해 식당의 대표 이미지를 검색합니다."
    )

    async def fetch(self, session: aiohttp.ClientSession, query: str):
        url = "https://openapi.naver.com/v1/search/image"
        headers = {
            "X-Naver-Client-Id": AGENT_NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": AGENT_NAVER_CLIENT_SECRET,
        }
        print(f"[네이버 이미지 검색어]: {query}")
        params = {
            "query": query,
            "display": 5,
            "sort": "sim",
            "filter": "large",
        }
        try:
            async with session.get(url, headers=headers, params=params) as response:
                data = await response.json()
                items = data.get("items", [])
                if not items:
                    return "https://via.placeholder.com/300x200?text=No+Image"
                return items[0].get(
                    "link", "https://via.placeholder.com/300x200?text=No+Image"
                )
        except Exception as e:
            print(f"네이버 이미지 검색 오류: {str(e)}")
            return "https://via.placeholder.com/300x200?text=Error"

    async def _arun(self, restaurant_list: List[str]) -> Dict[str, str]:
        results = {}
        async with aiohttp.ClientSession() as session:
            for restaurant in restaurant_list:
                results[restaurant] = await self.fetch(session, restaurant)
        return results

    def _run(self, restaurant_list: List[str]) -> Dict[str, str]:
        return asyncio.run(self._arun(restaurant_list))


# ------------------------- Restaurant Agent Service -------------------------
class RestaurantAgentService:
    """식당 추천을 위한 Agent 서비스"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RestaurantAgentService, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        """서비스 초기화"""
        self.llm = LLM(model="gpt-4o", temperature=0, api_key=OPENAI_API_KEY)
        # Tools 초기화
        self.tools = {
            "geocoding": GeocodingTool(),
            "restaurant_search": RestaurantBasicSearchTool(),
            "web_search": NaverWebSearchTool(),
            "image_search": NaverImageSearchTool(),
        }
        self.agents = self._create_agents()

    def _process_input(
        self, input_data: dict, prompt: Optional[str] = None
    ) -> tuple[dict, str]:
        """입력 데이터 전처리"""
        print(f"[입력 데이터] input_data: {input_data}")
        print(f"[프롬프트 입력] prompt: {prompt}")

        # 맛집 관련 유효 컨셉 필터링
        valid_concepts = [
            "맛집",
            "해산물 좋아",
            "고기 좋아",
            "가족 여행",
            "기념일",
            "낮술",
        ]
        filtered_concepts = [
            concept
            for concept in input_data.get("concepts", [])
            if concept in valid_concepts
        ]
        if not filtered_concepts:
            filtered_concepts = ["맛집"]
        print(f"[컨셉 필터링] filtered_concepts: {filtered_concepts}")

        input_data["concepts"] = filtered_concepts
        prompt_text = (
            f'추가 참고: "{prompt}" 도 참고하여 추천해주세요.\n' if prompt else ""
        )

        return input_data, prompt_text

    def _create_agents(self) -> Dict[str, Agent]:
        """Agent들을 생성하는 메서드"""
        return {
            "geocoding": Agent(
                role="좌표 조회 전문가",
                goal="사용자가 입력한 location(예: '부산광역시')의 위도와 경도를 조회하며, location 값은 그대로 유지한다.",
                backstory="나는 위치 데이터 전문가로, 입력된 location 값을 변경하지 않고 Google Geocoding API를 통해 좌표를 조회한다.",
                tools=[self.tools["geocoding"]],
                llm=self.llm,
                verbose=True,
                async_execution=True,
            ),
            "restaurant_search": Agent(
                role="맛집 기본 조회 전문가",
                goal="좌표 정보를 활용하여 식당의 기본 정보를 조회한다.",
                backstory="나는 맛집 데이터 분석 전문가로, Google Maps API를 사용하여 특정 위치의 식당 정보를 최대 40개까지 조회한다.",
                tools=[self.tools["restaurant_search"]],
                llm=self.llm,
                verbose=True,
                async_execution=True,
            ),
            "web_search": Agent(
                role="네이버 웹 검색 에이전트",
                goal="네이버 웹 검색 API를 사용해 식당의 텍스트 기반 세부 정보를 조회한다.",
                backstory="나는 네이버 웹 검색 전문가로, 식당의 상세 텍스트 정보를 제공합니다.",
                tools=[self.tools["web_search"]],
                llm=self.llm,
                verbose=True,
                async_execution=True,
            ),
            "image_search": Agent(
                role="네이버 이미지 검색 에이전트",
                goal="네이버 이미지 검색 API를 사용해 식당의 이미지 URL을 조회한다.",
                backstory="나는 네이버 이미지 검색 전문가로, 식당의 정확한 이미지를 제공합니다.",
                tools=[self.tools["image_search"]],
                llm=self.llm,
                verbose=True,
                async_execution=True,
            ),
            "final_recommendation": Agent(
                role="최종 추천 에이전트",
                goal="필터링된 맛집 후보와 네이버 텍스트 기반 세부 정보를, 여행 계획을 고려하여 최종 맛집 추천 리스트를 생성한다.",
                backstory="나는 데이터 구조화 전문가로, 후보 식당의 기본 정보, 네이버에서 수집한 텍스트 세부 정보와 여행 계획 정보를 종합하여 최종 추천 리스트를 구성한다.",
                tools=[self.tools["web_search"]],
                llm=self.llm,
                verbose=True,
                async_execution=True,
            ),
        }

    def _create_tasks(self, input_data: dict, prompt_text: str) -> List[Task]:
        """Task들을 생성하는 메서드"""
        return [
            Task(
                description=f"{input_data['main_location']}의 좌표 조회",
                agent=self.agents["geocoding"],
                expected_output="위치 좌표",
            ),
            Task(
                description="맛집 기본 정보 조회",
                agent=self.agents["restaurant_search"],
                expected_output="맛집 기본 정보 리스트",
            ),
            Task(
                description=f"""
                이전 단계에서 평점 4.0 이상, 리뷰 수 500개 이상으로 필터링된 {input_data['main_location']} 지역의 맛집 후보 리스트를 바탕으로, 각 식당의 
                세부 정보를 최신 검색 결과를 활용하여 가져오라. 
                검색 시 반드시 아래 JSON 스키마에 맞추어 정확하고 누락 없이 정보를 반환할 것. 
                특히, 아래 항목들은 최신 정보에 기반하여 모두 포함되어야 한다:
                
                {{
                    "kor_name": "string (가게 한글이름, 최대 255자)",
                    "eng_name": "string 또는 null (가게 영어이름, 최대 255자)",
                    "description": "string (가게 설명, 최대 255자)",
                    "address": "string (주소, 최대 255자)",
                    "url": "string 또는 null (웹사이트 URL, 최대 2083자)",
                    "image_url": "string (이미지 URL, 최대 2083자)",
                    "map_url": "string (map_url, 최대 2083자)",
                    "latitude": "number (위도)",
                    "longitude": "number (경도)",
                    "spot_category": "2",
                    "phone_number": "string 또는 null (전화번호, 최대 300자)",
                    "business_status": "string 또는 null (영업 상태)",
                    "business_hours": "string 또는 null (영업시간, 최대 255자)"
                }}
                
                위 JSON 스키마에 맞추어 모든 필드를 채워서 결과를 반환하라.
                """,
                agent=self.agents["web_search"],
                expected_output="각 후보 식당의 세부 정보(details_map)",
            ),
            Task(
                description=f"""이전 단계에서 평점 4.0 이상, 리뷰 수 500개 이상으로 필터링된 {input_data['main_location']} 지역의 맛집 후보 리스트를 바탕으로, 각 식당의 
                이미지를 최신 검색 결과를 활용하여 다음 조건을 만족하는 이미지를 검색하라
                - 반드시 실제 식당의 외관, 내부 또는 음식 사진을 선택할 것.
                - 이미지의 해상도는 최소 300x300 이상이며, 최신 1년 이내의 고화질 이미지를 우선으로 한다.
                - 로고, 지도, 텍스트가 포함된 이미지, 메뉴판 등은 제외한다.
                - 각 식당에 대해 조건을 모두 만족하는 이미지 URL을 반환하라.""",
                agent=self.agents["image_search"],
                expected_output="맛집 이미지 URL",
            ),
            Task(
                description=f"""
                이전 단계에서 수집한 {input_data['main_location']} 지역의 맛집 데이터를 바탕으로, 
                {input_data['start_date']}부터 {input_data['end_date']}까지 여행하는 {input_data['ages']} 연령대의 고객과 
                동반자({', '.join([f"{c['label']} {c['count']}명" for c in input_data['companion_count']])})의 
                {', '.join(input_data.get('concepts', ['맛집']))} 컨셉에 맞는 최종 맛집 리스트를 중복 없이 추천하라.
                {prompt_text}
                
                필수:
                - 만약, 추천된 식당 리스트의 개수가 위 조건에 맞는 최종 개수보다 적을 경우, 전체 후보 리스트(해산물 관련 여부와 무관하게)에서 중복 없이 부족한 항목을 보충하여 최종 리스트가 반드시 정해진 개수(하루 3끼 기준)가 되도록 하라.
                - spot_category는 2로 고정한다.
                - day_x는 가게가 추천되는 날(예: 1일차, 2일차 등)을 의미한다.
                - order는 해당 day_x 내에서의 추천 순서(아침: 1, 점심: 2, 저녁: 3)를 의미한다.
                - spot_time은 아침, 점심, 저녁 시간대를 hh:mm:ss 형식으로 표시해야 한다.
                - order와 day_x는 사용자의 여행 일정 일수에 맞게 조정되어야 한다.
                - 최종 맛집 리스트의 개수는 하루 3끼 기준으로 결정된다. (예: 1박 2일이면 총 6개 이상, 2박 3일이면 총 9개 이상)
                - 위도, 경도, 이미지 데이터는 이전 태스크들에서 얻은 정보를 활용한다.
                """,
                agent=self.agents["final_recommendation"],
                expected_output="최종 추천 맛집 리스트",
                output_pydantic=spots_pydantic,
            ),
        ]

    def _process_result(self, result, input_data: dict) -> dict:
        """결과를 처리하는 메서드"""
        if hasattr(result, "tasks_output") and result.tasks_output:
            final_task_output = result.tasks_output[-1]
            if hasattr(final_task_output, "pydantic"):
                spots_data = final_task_output.pydantic.model_dump()
            else:
                spots_data = json.loads(final_task_output.raw)
        else:
            spots_data = {"spots": []}

        return {
            "message": "요청이 성공적으로 처리되었습니다.",
            "plan": {
                "name": input_data.get("name", "여행 일정"),
                "start_date": input_data["start_date"],
                "end_date": input_data["end_date"],
                "main_location": input_data["main_location"],
                "ages": input_data.get("ages", 0),
                "companion_count": sum(
                    companion.get("count", 0)
                    for companion in input_data.get("companion_count", [])
                ),
                "concepts": ", ".join(input_data.get("concepts", [])),
                "member_id": input_data.get("member_id", 0),
                "created_at": datetime.now().strftime("%Y-%m-%d"),
                "updated_at": datetime.now().strftime("%Y-%m-%d"),
            },
            "spots": spots_data.get("spots", []),
        }

    async def create_recommendation(
        self, input_data: dict, prompt: Optional[str] = None
    ) -> dict:
        """추천 워크플로우를 실행하는 메서드"""
        try:
            # 1. 입력 데이터 전처리
            processed_input, prompt_text = self._process_input(input_data, prompt)

            # 2. Task 생성
            tasks = self._create_tasks(processed_input, prompt_text)

            # 3. Crew 실행
            crew = Crew(tasks=tasks, agents=list(self.agents.values()), verbose=True)

            # 4. 결과 처리
            result = await crew.kickoff_async()
            return self._process_result(result, processed_input)

        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))
