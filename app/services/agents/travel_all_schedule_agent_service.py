import json
import os
import asyncio
from crewai import Agent, Task, Crew, LLM
from datetime import datetime
from dotenv import load_dotenv
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class spot_pydantic(BaseModel):
    kor_name: str = Field(max_length=255)
    eng_name: str = Field(default=None, max_length=255)
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

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
llm = LLM(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY)

class KakaoMapRouteTool(BaseTool):
    name: str = "KakaoMapRoute"
    description: str = "여행 일정의 최적 경로를 계산하고 각 장소 간 거리 정보를 제공합니다."
    
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
    try:
        main_location = user_input.get("main_location", "Unknown Location")
        trip_days = calculate_trip_days(user_input["start_date"], user_input["end_date"])
        user_input["trip_days"] = trip_days
        from app.services.agents.site_agent import create_tourist_plan
        from app.services.agents.cafe_agent_service import cafe_agent
        from app.services.agents.restaurant_agent_service import create_recommendation

        # 외부 에이전트 호출
        agent_type = user_input.get("agent_type", [])
        
        tasks = {}
        if "restaurant" in agent_type:
            tasks["restaurant"] = asyncio.to_thread(create_recommendation,user_input)
        if "site" in agent_type:
            tasks["site"] = asyncio.to_thread(create_tourist_plan,user_input)
        if "cafe" in agent_type:
            tasks["cafe"] = cafe_agent(user_input)

        # 비동기 병렬 호출
        results = await asyncio.gather(*tasks.values())
        external_data = {key: result for key, result in zip(tasks.keys(), results)}
        # 통합 입력 데이터에 외부 데이터를 추가 (후속 작업에서 모두 참조할 수 있도록)
        user_input["external_data"] = external_data

        print("외부데이터 타입  =====================",type(tasks))

        # Task 생성: description 필드에 모든 지시문을 포함 (플레이스홀더 사용)
        planning_agent = Agent(
            role="여행 일정 최적화 플래너",
            goal="제공된 외부 데이터를 사용하여 여행 일정을 구성한다. 새로운 장소는 생성하지 않는다.",
            backstory="외부 데이터를 재배열하여 최종 여행 일정을 생성합니다.",
            tools=[KakaoMapRouteTool()],
            llm=llm,
            verbose=True,
        )
        planning_task = Task(
            description="""
            [최종 여행 일정 생성]
            - 여행 기간: {start_date} ~ {end_date} ({trip_days}일)
            - 위의 JSON 데이터를 그대로 활용하여, 날짜별로 최적의 순서로 재배열하고,
              각 장소의 방문 순서를 지정하세요.
            - 이동 거리와 시간을 고려하여 효율적인 동선을 구성하세요.
            -외부 데이터 : {external_data} <-- 반드시 사용 
            - {external_data} 안에 restaurant, site, cafe 키가 있고, 각각이 장소 목록을 담고 있다.
            - 아침 slot은 site(관광지)에서 1개, cafe에서 1개를 골라라.
            - 점심 slot은 restaurant(맛집)에서 1개, site(관광지)에서 2개를 골라라.
            - 저녁 slot은 restaurant(맛집)에서 1개, 그리고 숙소()는 external_data에 있다면 사용하고, 없으면 생략한다.
            - 만약 필요한 카테고리(restaurant, site, cafe)에 장소가 부족하면, 그 slot은 비워둔다(새로운 장소를 임의로 만들지 않는다).
            -여기서 외부 데이터만 가지고 위도 경도를 계산후 최적의 동선을 위에 일정 조율 .
            - day_x: 방문 날짜
            - order: 해당 날짜의 방문 순서
            - 나머지 필드는 그대로 유지
            """,
            agent=planning_agent,
            expected_output="pydantic 형식의 여행 일정 데이터",
            output_pydantic=spots_pydantic,
        )
        # Crew 실행: planning_agent를 사용하여 최종 일정 생성
        Crew(agents=[planning_agent], tasks=[planning_task], verbose=True).kickoff(inputs=user_input)
     
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
        return {"message": "요청 처리 중 오류가 발생했습니다.", "error": str(e)}
