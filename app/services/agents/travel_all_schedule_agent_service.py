import json
import re
import traceback
import os
import requests
import concurrent.futures
import asyncio
from crewai import Agent, Task, Crew, LLM
from datetime import datetime
from dotenv import load_dotenv
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from sqlalchemy import Column, Double
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World"}

# ──────────────────────────────
# pydantic 모델 정의 (여행 일정 결과)
# ──────────────────────────────
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
    latitude: float = None  
    longitude: float = None  
    distance_from_prev: float = None  

class spots_pydantic(BaseModel):
    spots: list[spot_pydantic]

# ──────────────────────────────
# 환경변수, LLM, Tool 설정
# ──────────────────────────────
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AGENT_NAVER_CLIENT_ID = os.getenv("AGENT_NAVER_CLIENT_ID")
AGENT_NAVER_CLIENT_SECRET = os.getenv("AGENT_NAVER_CLIENT_SECRET")
KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
llm = LLM(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY)

# 카카오 로컬 검색 툴
class KakaoLocalSearchTool(BaseTool):
    name: str = "KakaoLocalSearch"
    description: str = "카카오 로컬 API를 사용해 장소 정보를 검색 (키워드로)"
    def _run(self, query: str) -> str:
        kakao_key = os.getenv("KAKAO_CLIENT_ID")
        if not kakao_key:
            return "[KakaoLocalSearchTool] 카카오 API 자격 증명이 없습니다."
        url = "https://dapi.kakao.com/v2/local/search/keyword.json"
        headers = {"Authorization": f"KakaoAK {kakao_key}"}
        params = {"query": query, "size": 15, "page": 1}
        try:
            resp = requests.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            documents = data.get("documents", [])
            if not documents:
                return f"[KakaoLocalSearchTool] '{query}' 검색 결과 없음."
            results = []
            for doc in documents:
                results.append({
                    "place_name": doc.get("place_name", ""),
                    "category": doc.get("category_name", ""),
                    "address": doc.get("address_name", ""),
                    "road_address": doc.get("road_address_name", ""),
                    "phone": doc.get("phone", ""),
                    "latitude": float(doc.get("y", 0)),
                    "longitude": float(doc.get("x", 0))
                })
            return json.dumps(results, ensure_ascii=False)
        except Exception as e:
            return f"[KakaoLocalSearchTool] 에러: {str(e)}"

# 경로 계산 Tool (최적 경로 계산)
class KakaoMapRouteTool(BaseTool):
    name: str = "KakaoMapRoute"
    description: str = "여행 일정의 최적 경로를 계산하고 각 장소 간 거리 정보를 제공"
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        from math import radians, sin, cos, sqrt, atan2
        R = 6371  # km
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c

    def _run(self, spots: list) -> str:
        try:
            daily_spots = {}
            for spot in spots:
                day = spot.get("day_x", 1)
                daily_spots.setdefault(day, []).append(spot)
            
            optimized_routes = {}
            for day, places in daily_spots.items():
                route = []
                unvisited = places.copy()
                if not unvisited:
                    continue
                current = unvisited.pop(0)
                route.append(current)
                while unvisited:
                    min_dist = float('inf')
                    next_place = None
                    for place in unvisited:
                        dist = self.calculate_distance(
                            current["latitude"], current["longitude"],
                            place["latitude"], place["longitude"]
                        )
                        if dist < min_dist:
                            min_dist = dist
                            next_place = place
                    if next_place:
                        next_place["distance_from_prev"] = min_dist
                        route.append(next_place)
                        unvisited.remove(next_place)
                        current = next_place
                optimized_routes[day] = route
            return json.dumps(optimized_routes, ensure_ascii=False)
        except Exception as e:
            return f"[KakaoMapRouteTool] 에러: {str(e)}"

def extract_json_from_text(text: str) -> str:
    try:
        match = re.search(r"\[.*?\]", text, re.DOTALL)
        if match:
            return match.group(0)
    except Exception as e:
        print(f"JSON 추출 오류: {e}")
    return text

def extract_recommendations_from_output(output) -> list:
    try:
        if not isinstance(output, (str, bytes, bytearray)):
            output = str(output)
        json_str = extract_json_from_text(output)
        recommendations = json.loads(json_str)
        if isinstance(recommendations, list):
            return recommendations
        return []
    except Exception as e:
        print(f"파싱 오류: {e}")
        return []

# DummyTask: 외부 서비스 결과를 planning_task의 context로 전달하기 위한 래퍼
class DummyTask:
    def __init__(self, output):
        self.output = output

def calculate_trip_days(start_date_str, end_date_str):
    fmt = "%Y-%m-%d"
    start_dt = datetime.strptime(start_date_str, fmt)
    end_dt = datetime.strptime(end_date_str, fmt)
    delta = end_dt - start_dt
    return delta.days + 1

# ──────────────────────────────
# 최종 일정 생성 함수 (Aggregator)
# ──────────────────────────────
async def create_plan(user_input: dict):
    """
    외부 서비스 파일에 정의된 결과값(예: 음식점, 관광지, 숙소 추천 결과)을 받아서,
    planning_agent가 이 데이터를 바탕으로 최적 경로를 고려한 여행 일정을 생성한다.
    
    user_input 예시:
    {
        "name": "나의 여행 일정",
        "start_date": "2025-03-01",
        "end_date": "2025-03-05",
        "main_location": "서울",
        "selected_options": ["restaurant", "site"]  # 예: 음식점과 관광지 선택
    }
    """
    try:
        main_location = user_input.get("main_location", "Unknown Location")
        trip_days = calculate_trip_days(user_input["start_date"], user_input["end_date"])
        selected = user_input.get("selected_options", [])

        # 외부 서비스 결과 호출
        # 실제 경로와 함수명은 프로젝트에 맞게 수정하세요.
        from app.services.agents.site_agent12 import create_restaurant_plan
        from app.services.agents.cafe_agent_service import cafe_agent
        from app.services.agents.accommodation_agent_3 import run as run_accommodation

        context_tasks = []
        if "site" in selected:
            site_result = create_restaurant_plan(user_input)
            context_tasks.append(DummyTask({"site_result": site_result}))
        if "accommodation" in selected:
            accommodation_result = run_accommodation(user_input)
            context_tasks.append(DummyTask({"accommodation_result": accommodation_result}))
        if "cafe" in selected:
            cafe_result = cafe_agent(user_input)
            context_tasks.append(DummyTask({"cafe_result": cafe_result}))
        
        if not context_tasks:
            raise ValueError("최소 한 가지 서비스 옵션(restaurant, site, accommodation, cafe)을 선택해야 합니다.")

        # planning_agent 생성 (최종 일정 생성 전용)
        # 여기서 플래닝 에이전트는 오직 context로 전달된 외부 결과만을 참고하여 일정을 생성한다.
        planning_agent = Agent(
            role="여행 일정 플래너",
            goal=(
                "외부 서비스에서 받은 여행 스팟 정보(예: 음식점, 관광지, 숙소, 카페 추천 결과)만을 사용하여, "
                "최적 경로와 이동 시간을 고려한 전체 여행 일정을 생성하라. "
                "참고 자료나 추가 입력 없이, 오직 전달된 서비스 결과만으로 일정을 구성해야 한다."
            ),
            backstory="나는 오직 외부 에이전트 결과만을 기반으로 여행 동선과 최적 경로를 계산하는 AI 플래너이다.",
            tools=[KakaoLocalSearchTool(), KakaoMapRouteTool()],
            llm=llm,
            verbose=True,
        )

        planning_task = Task(
            description="""
            [최종 여행 일정 생성]
            - 여행 기간: {start_date} ~ {end_date} (총 {trip_days}일)
            - 외부 서비스 결과만을 활용하여, 최적 경로 및 이동 시간을 고려한 여행 스팟 리스트를 JSON 형식으로 생성하라.
            - 각 스팟에는 day_x, order, spot_category 등의 필드를 포함해야 한다.
            """,
            agent=planning_agent,
            context=context_tasks,  # 외부 서비스 결과 DummyTask 객체들을 context로 전달
            expected_output="pydantic 형식의 여행 일정 데이터",
            output_pydantic=spots_pydantic,
            async_execution=False,
        )

        # Crew 실행: planning_agent를 사용하여 최종 일정 생성
        Crew(agents=[planning_agent], tasks=[planning_task], verbose=True).kickoff(inputs=user_input)
        
        print("최종 결과:", planning_task.output.pydantic.model_dump())
        response_json = {
            "message": "요청이 성공적으로 처리되었습니다.",
            "plan": {
                "name": user_input.get("name", "여행 일정"),
                "start_date": user_input["start_date"],
                "end_date": user_input["end_date"],
                "main_location": main_location,
                "created_at": datetime.now().strftime("%Y-%m-%d"),
            },
            "spots": planning_task.output.pydantic.model_dump()
        }
        
        return response_json

    except Exception as e:
        print(f"[ERROR] {e}")
        traceback.print_exc()
        return {"message": "요청 처리 중 오류가 발생했습니다.", "error": str(e)}
