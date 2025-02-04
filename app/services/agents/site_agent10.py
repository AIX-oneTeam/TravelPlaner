import json
import traceback
import os
import requests
from crewai import Agent, Task, Crew, LLM
from dotenv import load_dotenv
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from fastapi import FastAPI
from typing import Optional

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Hello World"}


# ──────────────────────────────
# 1. Request 모델 정의 (관광지 추천 입력)
# ──────────────────────────────
class TouristFeedback(BaseModel):
    tourist: bool = False  # False: 초안 추천, True: 대체 추천 요청


# location은 이제 기본값 없이 사용자가 반드시 입력하도록 변경
class TouristPlanRequest(BaseModel):
    location: str
    feedback: TouristFeedback = TouristFeedback()


# ──────────────────────────────
# 2. pydantic 모델 정의 (관광지 정보)
# ──────────────────────────────
class Spot(BaseModel):
    kor_name: str = Field(..., max_length=255)
    eng_name: str = Field(default=None, max_length=255)
    description: str = Field(..., max_length=255)
    address: str = Field(..., max_length=255)
    zip: str = Field(..., max_length=10)
    url: str = Field(default=None, max_length=2083)
    image_url: str = Field(..., max_length=2083)
    map_url: str = Field(..., max_length=2083)
    likes: int = None
    satisfaction: float = None
    # 관광지인 경우 spot_category는 1로 고정
    spot_category: int = 1
    phone_number: str = Field(default=None, max_length=300)
    business_status: bool = None
    business_hours: str = Field(default=None, max_length=255)


class Spots(BaseModel):
    spots: list[Spot]


# ──────────────────────────────
# 3. 환경변수, LLM, Tool 설정
# ──────────────────────────────
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AGENT_NAVER_CLIENT_ID = os.getenv("AGENT_NAVER_CLIENT_ID")
AGENT_NAVER_CLIENT_SECRET = os.getenv("AGENT_NAVER_CLIENT_SECRET")

llm = LLM(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY)


class NaverWebSearchTool(BaseTool):
    """네이버 웹 검색 API를 사용해 텍스트 정보를 검색"""

    name: str = "NaverWebSearch"
    description: str = "네이버 웹 검색 API를 사용해 텍스트 정보를 검색"

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


# ──────────────────────────────
# 4. 관광지 추천 기능 (초안 + 대체 추천)
# ──────────────────────────────
def create_tourist_plan(user_input: dict):
    """
    CrewAI를 사용하여 관광지 추천 초안을 생성합니다.
    user_input 예시:
    {
        "location": "입력한 지역명",
        "feedback": {"tourist": True}  # True이면 대체 추천 진행
    }
    """
    try:
        # 반드시 입력된 지역명을 사용합니다.
        location = user_input["location"]

        # 4-1. 초기 관광지 추천 에이전트
        tourist_agent = Agent(
            role="관광지 추천 에이전트",
            goal=f"사용자에게 {location} 지역 내에서 문화, 역사, 자연경관 등 다양한 측면을 종합적으로 고려한 독창적이고 체계적인 관광지 추천을 제공하라.",
            backstory=f"""
            나는 {location} 지역의 관광지에 대해 심도 있는 정보를 보유하고 있으며, 최신 트렌드, 문화, 역사 및 자연 경관을 반영한 데이터를 기반으로 분석하는 전문가입니다.
            수년간의 현장 경험과 다양한 데이터 소스를 활용하여 {location}의 주요 명소와 숨겨진 보석 같은 관광지를 체계적으로 추천할 수 있습니다.
            내 분석은 지역의 문화적 배경, 역사적 가치, 자연미와 함께 최신 관광 트렌드와 사용자 선호도를 모두 고려하여, 사용자가 잊지 못할 특별한 경험을 할 수 있도록 돕습니다.
            """,
            tools=[NaverWebSearchTool()],
            llm=llm,
            verbose=True,
        )

        # 4-2. 대체 관광지 추천 에이전트
        alternative_tourist_agent = Agent(
            role="대체 관광지 추천 에이전트",
            goal=f"{location} 지역 내 기존 추천과 차별화된, 숨겨진 명소나 덜 알려진 관광지를 발굴하여 사용자에게 제시하라.",
            backstory=f"""
            나는 {location} 지역의 다양한 관광지를 심도 있게 분석하고, 현장 조사와 최신 데이터를 기반으로 일반적으로 널리 알려진 관광지와는 다른 특별하고 새로운 명소를 발굴하는 전문가입니다.
            내 접근 방식은 지역 주민 인터뷰, 최신 관광 트렌드, 그리고 다각도의 데이터 분석을 통해 {location}의 숨겨진 매력을 찾아내는 데 중점을 두고 있으며,
            이를 통해 사용자가 기존 추천과는 다른, 독창적이고 참신한 관광지를 경험할 수 있도록 도와줍니다.
            """,
            tools=[NaverWebSearchTool()],
            llm=llm,
            verbose=True,
        )

        # 4-3. 초안 관광지 추천 태스크 생성
        tourist_task = Task(
            description=f"""
            ['{location}' 관광지 초안 추천]
            - {location} 인근의 관광지를 최소 5곳 추천하라.
            - 각 관광지에 대해 상세한 주소, 주요 특징, 추천 이유 및 관련 정보(예: 운영 시간, 접근성 등)를 포함하라.
            """,
            agent=tourist_agent,
            expected_output="관광지 추천 결과 (텍스트)",
        )

        tasks = [tourist_task]

        # 4-4. 사용자의 피드백에 따라 대체 추천 태스크 추가
        if user_input.get("feedback", {}).get("tourist", False):
            alternative_task = Task(
                description=f"""
                [대체 '{location}' 관광지 추천]
                - 기존 초안 추천과 차별화된 {location} 인근의 관광지를 최소 5곳 추천하라.
                - 각 관광지에 대해 상세한 주소, 주요 특징, 추천 이유 및 기타 부가 정보를 포함하라.
                """,
                agent=alternative_tourist_agent,
                expected_output="대체 관광지 추천 결과 (텍스트)",
            )
            tasks.append(alternative_task)

        # 4-5. Crew 실행
        crew = Crew(
            agents=[tourist_agent, alternative_tourist_agent],
            tasks=tasks,
            verbose=True,
        )
        crew.kickoff()

        # 피드백 여부에 따라 대체 태스크 결과 또는 초안 결과 선택
        if user_input.get("feedback", {}).get("tourist", False):
            alternative_output = None
            for task in tasks:
                if task.agent == alternative_tourist_agent:
                    alternative_output = task.output
                    break
            result = alternative_output if alternative_output else tourist_task.output
        else:
            result = tourist_task.output

        response_json = {
            "message": "관광지 추천이 완료되었습니다.",
            "location": location,
            "recommendation": result,
        }

        return response_json

    except Exception as e:
        print(f"[ERROR] {e}")
        traceback.print_exc()
        return {"message": "관광지 추천 처리 중 오류가 발생했습니다.", "error": str(e)}


# ──────────────────────────────
# 5. FastAPI 엔드포인트 (POST /tourist_plan)
# ──────────────────────────────
@app.post("/tourist_plan")
def get_tourist_plan(request: TouristPlanRequest):
    """
    Swagger UI (http://127.0.0.1:8000/docs)에서
    location과 feedback 값을 입력하여 관광지 추천 요청을 보낼 수 있습니다.
    """
    result = create_tourist_plan(request.dict())
    return result
