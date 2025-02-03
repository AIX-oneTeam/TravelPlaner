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


class TouristPlanRequest(BaseModel):
    location: str = "강릉"
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
    CrewAI를 사용하여 강릉 관광지 추천 초안을 생성합니다.
    user_input 예시:
    {
        "location": "강릉",
        "feedback": {"tourist": True}  # True이면 대체 추천 진행
    }
    """
    try:
        location = user_input.get("location", "강릉")

        # 4-1. 초기 관광지 추천 에이전트
        tourist_agent = Agent(
            role="관광지 추천 에이전트",
            goal=f"'{location}' 인근의 관광지를 추천",
            backstory="""
            나는 강릉 지역의 관광지에 대해 깊이 있는 지식을 보유한 전문가이다.
            최신 트렌드와 지역 특성을 반영해 매력적인 관광지를 추천할 수 있다.
            """,
            tools=[NaverWebSearchTool()],
            llm=llm,
            verbose=True,
        )

        # 4-2. 대체 관광지 추천 에이전트 (초안 추천에 불만족 시)
        alternative_tourist_agent = Agent(
            role="대체 관광지 추천 에이전트",
            goal=f"'{location}' 인근의 기존 추천과 다른 새로운 관광지를 추천",
            backstory="""
            나는 강릉 지역의 다양한 관광지를 심도 있게 분석해, 기존 추천과 차별화된 관광지를 찾아내는 전문가이다.
            """,
            tools=[NaverWebSearchTool()],
            llm=llm,
            verbose=True,
        )

        # 4-3. 초안 관광지 추천 태스크 생성
        tourist_task = Task(
            description=f"""
            [강릉 관광지 초안 추천]
            - '{location}' 인근의 관광지를 최소 5곳 추천.
            - 각 관광지에 대해 주소, 특징, 추천 이유 등을 포함.
            """,
            agent=tourist_agent,
            expected_output="관광지 추천 결과 (텍스트)",
        )

        tasks = [tourist_task]

        # 4-4. 사용자의 피드백에 따라 대체 추천 태스크 추가
        if user_input.get("feedback", {}).get("tourist", False):
            alternative_task = Task(
                description=f"""
                [대체 강릉 관광지 추천]
                - 기존 초안 추천과 다른 '{location}' 인근의 관광지를 최소 5곳 추천.
                - 각 관광지에 대해 주소, 특징, 추천 이유 등을 포함.
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

        # 피드백이 있을 경우 대체 태스크 결과를, 아니면 초안 결과를 사용
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
