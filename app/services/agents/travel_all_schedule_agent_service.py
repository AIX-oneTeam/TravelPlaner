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
# 환경변수, LLM 설정
# ──────────────────────────────
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AGENT_NAVER_CLIENT_ID = os.getenv("AGENT_NAVER_CLIENT_ID")
AGENT_NAVER_CLIENT_SECRET = os.getenv("AGENT_NAVER_CLIENT_SECRET")
KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
llm = LLM(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY)

# ──────────────────────────────
# 카카오 로컬 검색 툴
# ──────────────────────────────
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

# ──────────────────────────────
# 기타 helper 함수들
# ──────────────────────────────
def extract_json_from_text(text: str) -> str:
    try:
        match = re.search(r"\[.*?\]", text, re.DOTALL)
        if match:
            return match.group(0)
    except Exception as e:
        print(f"JSON 추출 오류: {e}")
    return text

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
    외부 서비스 결과(예: 음식점, 관광지, 숙소, 카페 추천 결과)를 받아서,
    planning_agent가 이 데이터를 바탕으로 최적 경로를 고려한 여행 일정을 생성한다.
    
    user_input 예시:
    {
        "name": "나의 여행 일정",
        "start_date": "2025-03-01",
        "end_date": "2025-03-05",
        "main_location": "서울",
        "selected_options": ["restaurant", "site", "cafe"]
    }
    """
    try:
        main_location = user_input.get("main_location", "Unknown Location")
        trip_days = calculate_trip_days(user_input["start_date"], user_input["end_date"])
        selected = user_input.get("selected_options") or user_input.get("agent_type") or []
        user_input["trip_days"] = trip_days     

        # 외부 서비스 결과 호출
        from app.services.agents.site_agent import create_tourist_plan
        from app.services.agents.cafe_agent_service import cafe_agent
        from app.services.agents.accommodation_agent_3 import run as run_accommodation

        context_tasks = []
        if "site" in selected:
            site_result = create_tourist_plan(user_input)
            context_tasks.append({
                "site_result": site_result,
                "description": "Tourist site recommendations",
                "expected_output": json.dumps(site_result, ensure_ascii=False)
            })
        if "accommodation" in selected:
            accomodation_result = run_accommodation(user_input)
            context_tasks.append({
                "accomodation_result": accomodation_result,
                "description": "Accommodation recommendations",
                "expected_output": json.dumps(accomodation_result, ensure_ascii=False)
            })
        if "cafe" in selected:
            cafe_result = await cafe_agent(user_input)
            context_tasks.append({
                "cafe_result": cafe_result,
                "description": "Cafe recommendations",
                "expected_output": json.dumps(cafe_result, ensure_ascii=False)
            })

        # 디버깅: 외부 서비스 결과 출력 (단순 json.dumps 사용)
        try:
            external_data = json.dumps(context_tasks, ensure_ascii=False, indent=2)
            # 중괄호 이스케이프 처리
            escaped_external_data = external_data.replace("{", "{{").replace("}", "}}")
            print("DEBUG: 외부 서비스 결과 (context_tasks):")
            print(escaped_external_data)
        except Exception as e:
            print(f"[DEBUG ERROR] JSON 직렬화 실패: {e}")
        
        if not context_tasks:
            raise ValueError("최소 한 가지 서비스 옵션(restaurant, site, accommodation, cafe)을 선택해야 합니다.")

        # 프롬프트 지시문 구성
        prompt_instruction = (
            "다음 JSON 데이터는 외부 서비스로부터 받은 실제 추천 장소 정보입니다. "
            "아래 데이터를 그대로 사용하여, 새로운 장소나 임의의 데이터를 생성하지 말고, 이 데이터를 재배열하여 일정 초안을 작성하세요.\n\n"
            "=== 외부 데이터 ===\n"
            f"{escaped_external_data}\n"
            "=== 끝 ===\n\n"
        )
        
        # planning_agent 생성 (tools는 사용하지 않음)
        planning_agent = Agent(
            role="여행 일정 최적화 플래너",
            goal=(
                "위에 제공된 외부 JSON 데이터를 그대로 사용하여, 일정 초안을 작성합니다. "
                "절대 새로운 장소를 생성하지 마세요."
            ),
            backstory=(
                "나는 외부 서비스에서 받은 실제 장소 데이터만을 사용하여 일정을 구성합니다. "
                "제공된 JSON 데이터를 재구성하여 최종 출력에 반영합니다."
            ),
            tools=[],
            llm=llm,
            verbose=True,
        )
        
        print("DEBUG: planning_agent에 전달될 context_tasks:")
        print(json.dumps(context_tasks, ensure_ascii=False, indent=2))
        
        planning_task = Task(
            description=prompt_instruction + """
            [최종 여행 일정 생성]
            - 여행 기간: {start_date} ~ {end_date} ({trip_days}일)
            - 위의 JSON 데이터를 그대로 활용하여, 날짜별로 최적의 순서로 재배열하고,
              각 장소의 방문 순서를 지정하세요.
            - 이동 거리와 시간을 고려하여 효율적인 동선을 구성하세요.
            
            출력 형식 (pydantic 모델 준수):
            - 각 장소는 반드시 위 JSON 데이터에서 제공된 것이어야 합니다.
            - day_x: 방문 날짜
            - order: 해당 날짜의 방문 순서
            - 나머지 필드는 그대로 유지
            """,
            agent=planning_agent,
            context=context_tasks,
            expected_output="pydantic 형식의 여행 일정 데이터",
            output_pydantic=spots_pydantic,
            async_execution=False,
        )

        Crew(agents=[planning_agent], tasks=[planning_task], verbose=True).kickoff(inputs=user_input)
        
        if hasattr(planning_task.output, 'raw'):
            print("DEBUG: planning_task.raw 출력:")
            print(planning_task.output.raw)
        
        print("DEBUG: 최종 planning_task의 pydantic 모델 출력:")
        
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
