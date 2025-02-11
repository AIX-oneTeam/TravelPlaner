import json
import os
from crewai import Agent, Task, Crew, LLM
from dotenv import load_dotenv
from crewai.tools import BaseTool
from app.dtos.spot_models import spots_pydantic, calculate_trip_days
from datetime import datetime
from app.utils.time_check import time_check

load_dotenv()
KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
llm = LLM(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY)


import os
import requests
import json
from dotenv import load_dotenv
from crewai.tools import BaseTool

class KakaoMapRouteTool(BaseTool):
    name: str = "KakaoMapRoute"
    description: str = "여행 일정의 최적 경로를 계산하고 각 장소 간 거리 정보를 제공합니다."

    def _run(self, spots: list) -> str:
        try:
            if len(spots) < 2:
                return json.dumps({"error": "최소 두 개 이상의 장소가 필요합니다."}, ensure_ascii=False)

            # 출발지 설정 (첫 번째 장소)
            origin = {
                "name": spots[0].get("kor_name", ""),
                "x": spots[0]["longitude"],
                "y": spots[0]["latitude"]
            }

            # 목적지 설정 (마지막 장소)
            destination = {
                "name": spots[-1].get("kor_name", ""),
                "x": spots[-1]["longitude"],
                "y": spots[-1]["latitude"]
            }

            # 경유지 설정 (중간 장소들)
            waypoints = [
                {
                    "name": spot.get("kor_name", ""),
                    "x": spot["longitude"],
                    "y": spot["latitude"]
                }
                for spot in spots[1:-1]
            ]

            # API 요청 본문 생성
            payload = {
                "origin": origin,
                "destination": destination,
                "waypoints": waypoints,
                "priority": "RECOMMEND"
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"KakaoAK {KAKAO_CLIENT_ID}"
            }

            # API 요청
            response = requests.post(
                "https://apis-navi.kakaomobility.com/v1/waypoints/directions",
                headers=headers,
                data=json.dumps(payload)
            )

            if response.status_code == 200:
                route_data = response.json()
                # 경로 최적화 결과를 spots에 반영
                optimized_spots = []
                for route in route_data.get("routes", []):
                    for section in route.get("sections", []):
                        for guide in section.get("guides", []):
                            location = guide.get("location", {})
                            lat = location.get("y")
                            lon = location.get("x")
                            # 원래의 spot 정보와 매칭하여 추가 정보 보존
                            for spot in spots:
                                if spot["latitude"] == lat and spot["longitude"] == lon:
                                    optimized_spot = spot.copy()
                                    optimized_spot["distance_from_prev"] = guide.get("distance", 0)
                                    optimized_spots.append(optimized_spot)
                                    break
                return json.dumps(optimized_spots, ensure_ascii=False)
            else:
                return json.dumps({"error": f"API 요청 실패: {response.status_code}"}, ensure_ascii=False)

        except Exception as e:
            return json.dumps({"error": f"[KakaoMapRouteTool] 에러: {str(e)}"}, ensure_ascii=False)



class TravelScheduleAgentService:
    """
    여행 일정 에이전트 인스턴스를 싱글톤 패턴으로 관리하는 클래스
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TravelScheduleAgentService, cls).__new__(cls)
            cls._instance.initialize()  # 최초 한 번만 초기화
        return cls._instance

    def initialize(self):
        print("TravelScheduleAgentService 초기화 중...")
        self.llm = llm
        self.route_tool = KakaoMapRouteTool()
        
        self.planner = Agent(
            role="여행 일정 최적화 플래너",
            goal="제공된 외부 데이터를 사용하여 여행 일정을 구성한다. 새로운 장소는 생성하지 않는다.",
            backstory="외부 데이터를 재배열하여 최종 여행 일정을 생성합니다.",
            tools=[self.route_tool],
            llm=self.llm,
            verbose=True,
        )
        self.crew = None

    @time_check
    async def create_plan(self, user_input: dict):
        try:
            main_location = user_input.get("main_location", "Unknown Location")
            trip_days = calculate_trip_days(user_input["start_date"], user_input["end_date"])
            user_input["trip_days"] = trip_days

            external_data = user_input.get("external_data", {})
            print("create_plan 내부에서 받은 external_data:", external_data)

            planning_task = Task(
                description="""
            [최종 여행 일정 생성]
            - 여행 기간: {start_date} ~ {end_date} ({trip_days}일)
            - 위의 JSON 데이터를 그대로 활용하여, 날짜별로 최적의 순서로 재배열하고,
              각 장소의 방문 순서를 지정하세요.
            - 이동 거리와 시간을 고려하여 효율적인 동선을 구성하세요.
            - 외부 데이터 : {external_data} <-- 반드시 사용 
            - {external_data} 안에 restaurant, site, cafe 키가 있고, 각각이 장소 목록을 담고 있다.
            - 아침 08:00 site(관광지)에서 1개, cafe에서 1개를 넣는다.
            - 점심 12:00 restaurant(맛집)에서 1개, site(관광지)에서 2개를 넣는다.
            - 저녁 18:00 restaurant(맛집)에서 1개, 그리고 숙소()는 external_data에 있다면 사용하고, 없으면 생략하고 넣는다.
            - 만약 필요한 카테고리(restaurant, site, cafe)에 장소가 부족하면, 그 slot은 비워둔다(새로운 장소를 임의로 만들지 않는다).
            - 여기서 외부 데이터만 가지고 도구를 사용하여 위도 경도를 계산 후 최적의 동선을 위에 일정 조율.
            - day_x: 방문 날짜
            - order: 해당 날짜의 방문 순서
            - 나머지 필드는 그대로 유지
                """,
                agent=self.planner,
                expected_output="pydantic 형식의 여행 일정 데이터",
                output_pydantic=spots_pydantic,
            )

            Crew(agents=[self.planner], tasks=[planning_task], verbose=True).kickoff(inputs=user_input)
                    
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
