import json
import re
import traceback
import os
import requests
import concurrent.futures
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
# 1. Request 모델 정의 (음식점 추천 입력)
# ──────────────────────────────
class RestaurantFeedback(BaseModel):
    restaurant: bool = False  # False: 초안 추천, True: 대체 추천 요청


# location은 반드시 사용자가 입력 (기본값 제거)
class RestaurantPlanRequest(BaseModel):
    location: str
    feedback: RestaurantFeedback = RestaurantFeedback()


# ──────────────────────────────
# 2. pydantic 모델 정의 (음식점 정보)
# ──────────────────────────────
class Restaurant(BaseModel):
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
    restaurant_category: int = 2  # 음식점이면 2로 고정 (예시)
    phone_number: str = Field(default=None, max_length=300)
    business_status: bool = None
    business_hours: str = Field(default=None, max_length=255)


class Restaurants(BaseModel):
    restaurants: list[Restaurant]


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
# 추가: 네이버 이미지 검색 도구 정의 (음식점에 맞게 수정)
# ──────────────────────────────
class NaverImageSearchTool(BaseTool):
    """네이버 이미지 검색 API를 사용해 이미지 URL을 가져옴"""

    name: str = "NaverImageSearch"
    description: str = "네이버 이미지 검색 API를 사용해 음식점에 맞는 이미지 URL을 검색"

    def _run(self, query: str) -> str:
        if not AGENT_NAVER_CLIENT_ID or not AGENT_NAVER_CLIENT_SECRET:
            return "[NaverImageSearchTool] 네이버 API 자격 증명이 없습니다."
        url = "https://openapi.naver.com/v1/search/image";
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
            if not items:
                return ""
            return items[0].get("link", "")
        except Exception as e:
            return f"[NaverImageSearchTool] 에러: {str(e)}"


# ──────────────────────────────
# 헬퍼 함수: JSON 배열 추출
# ──────────────────────────────
def extract_json_from_text(text: str) -> str:
    """
    문자열 내에서 첫 번째 JSON 배열([ ... ])을 추출합니다.
    """
    try:
        # non-greedy match를 사용하여 첫 번째 JSON 배열을 추출
        match = re.search(r"\[.*?\]", text, re.DOTALL)
        if match:
            return match.group(0)
    except Exception as e:
        print(f"JSON 추출 오류: {e}")
    return text


# ──────────────────────────────
# 헬퍼 함수: 추천 결과에서 음식점 목록(JSON 문자열)을 파싱
# ──────────────────────────────
def extract_recommendations_from_output(output) -> list:
    """
    에이전트 태스크의 output이 순수한 JSON 문자열임을 가정하고 파싱합니다.
    만약 출력에 추가 텍스트가 포함되어 있다면, 첫 번째 JSON 배열만 추출합니다.
    """
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


# ──────────────────────────────
# 헬퍼 함수: 개별 음식점 이름을 기반으로 이미지 URL 검색 (병렬 실행용)
# ──────────────────────────────
def get_image_url_for_place(place_name: str) -> str:
    tool = NaverImageSearchTool()
    return tool._run(place_name)


def add_images_to_recommendations(recommendations: list) -> list:
    """
    음식점 추천 리스트(딕셔너리 리스트)에 대해, 각 음식점의 'name'을 기반으로
    NaverImageSearchTool을 병렬 호출하여 'image_url' 필드를 추가한다.
    """
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_place = {
            executor.submit(get_image_url_for_place, place.get("name", "")): place
            for place in recommendations
        }
        for future in concurrent.futures.as_completed(future_to_place):
            place = future_to_place[future]
            try:
                image_url = future.result()
            except Exception as e:
                image_url = ""
            place["image_url"] = image_url
    return recommendations


# ──────────────────────────────
# 4. 음식점 추천 기능 (초안 + 대체 추천) 및 이미지 추가
# ──────────────────────────────
def create_restaurant_plan(user_input: dict):
    """
    CrewAI를 사용하여 음식점 추천 초안을 생성한 후, 각 음식점에 맞는 사진 URL을 추가합니다.
    **중요**: 모든 태스크의 프롬프트 및 expected_output에는 반드시 순수한 JSON 형식(추가 설명 없이)을 반환하도록 명시해야 합니다.
    user_input 예시:
    {
        "location": "입력한 지역명",
        "feedback": {"restaurant": True}  # True이면 대체 추천 진행
    }
    """
    try:
        location = user_input["location"]

        # 4-1. 초기 음식점 추천 에이전트
        restaurant_agent = Agent(
            role="음식점 추천 에이전트",
            goal=f'사용자에게 {location} 지역 내에서 다양한 음식점 정보를 JSON 배열 형태(예: [{{"name": "음식점명", "address": "...", "features": "...", "recommendation_reason": "...", "operating_hours": "...", "accessibility": "..."}}])로 반환하라. 다른 텍스트는 포함하지 말라.',
            backstory=f"""
            나는 {location} 지역의 음식점에 대해 심도 있는 정보를 보유한 전문가이다.
            수년간의 현장 경험과 다양한 데이터 소스를 활용하여 {location}의 인기 음식점과 숨은 맛집을 추천할 수 있다.
            내 분석은 음식의 종류, 분위기, 가격대, 고객 리뷰 등을 고려하며, 결과는 반드시 순수한 JSON 형식으로 출력되어야 한다.
            """,
            tools=[NaverWebSearchTool()],
            llm=llm,
            verbose=True,
        )

        # 4-2. 대체 음식점 추천 에이전트 (피드백이 있을 경우)
        alternative_restaurant_agent = Agent(
            role="대체 음식점 추천 에이전트",
            goal=f"{location} 지역 내 기존 추천과 차별화된 음식점 정보를 JSON 배열 형식(순수 JSON)으로 반환하라. 다른 부가 설명 없이 오직 JSON 데이터만 출력하라.",
            backstory=f"""
            나는 {location} 지역의 다양한 음식점을 심도 있게 분석하고, 기존에 널리 알려진 정보와는 차별화된 맛집을 발굴하는 전문가이다.
            내 접근 방식은 최신 음식 트렌드와 지역 데이터를 기반으로 하며, 결과는 반드시 순수한 JSON 배열로만 출력되어야 한다.
            """,
            tools=[NaverWebSearchTool()],
            llm=llm,
            verbose=True,
        )

        # 4-3. 초안 음식점 추천 태스크 생성 (반드시 순수 JSON만 반환하도록 지시)
        restaurant_task = Task(
            description=f"""
            ['{location}' 음식점 초안 추천]
            - {location} 인근의 음식점을 최소 5곳 추천하라.
            - 각 음식점에 대해 상세한 주소, 주요 특징, 추천 이유 및 관련 정보를 포함하라.
            - 결과는 반드시 순수한 JSON 배열로 반환하라. (예: [{{"name": "음식점명", "address": "...", "features": "...", "recommendation_reason": "...", "operating_hours": "...", "accessibility": "..."}}])
            """,
            agent=restaurant_agent,
            expected_output="음식점 추천 결과 (JSON 형식)",
        )

        tasks = [restaurant_task]

        # 4-4. 사용자의 피드백에 따라 대체 추천 태스크 추가 (순수 JSON 반환)
        if user_input.get("feedback", {}).get("restaurant", False):
            alternative_task = Task(
                description=f"""
                [대체 '{location}' 음식점 추천]
                - 기존 초안 추천과 차별화된 {location} 인근의 음식점을 최소 5곳 추천하라.
                - 각 음식점에 대해 상세한 주소, 주요 특징, 추천 이유 및 기타 부가 정보를 포함하라.
                - 결과는 반드시 순수한 JSON 배열로 반환하라.
                """,
                agent=alternative_restaurant_agent,
                expected_output="대체 음식점 추천 결과 (JSON 형식)",
            )
            tasks.append(alternative_task)

        # 4-5. Crew 실행 (음식점 추천 에이전트들)
        crew = Crew(
            agents=[restaurant_agent, alternative_restaurant_agent],
            tasks=tasks,
            verbose=True,
        )
        crew.kickoff()

        # 피드백 여부에 따라 대체 태스크 결과 또는 초안 결과 선택
        if user_input.get("feedback", {}).get("restaurant", False):
            alternative_output = None
            for task in tasks:
                if task.agent == alternative_restaurant_agent:
                    alternative_output = task.output
                    break
            raw_output = (
                alternative_output if alternative_output else restaurant_task.output
            )
        else:
            raw_output = restaurant_task.output

        # raw_output은 순수 JSON이어야 하므로 바로 파싱 시도
        recommendations = extract_recommendations_from_output(raw_output)

        # 4-6. 각 음식점에 대해 이미지 URL 추가 (병렬 처리)
        recommendations_with_images = add_images_to_recommendations(recommendations)

        response_json = {
            "message": "음식점 추천이 완료되었습니다.",
            "location": location,
            "recommendation": recommendations_with_images,
        }
        return response_json

    except Exception as e:
        print(f"[ERROR] {e}")
        traceback.print_exc()
        return {"message": "음식점 추천 처리 중 오류가 발생했습니다.", "error": str(e)}


# ──────────────────────────────
# 5. FastAPI 엔드포인트 (POST /restaurant_plan)
# ──────────────────────────────
@app.post("/restaurant_plan")
def get_restaurant_plan(request: RestaurantPlanRequest):
    """
    Swagger UI (http://127.0.0.1:8000/docs)에서
    location과 feedback 값을 입력하여 음식점 추천 요청을 보낼 수 있습니다.
    """
    result = create_restaurant_plan(request.dict())
    return result
