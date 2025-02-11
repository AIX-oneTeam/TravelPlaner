import json 
import re
import traceback
import os
import requests
import concurrent.futures
from decimal import Decimal
from sqlalchemy import Column, Numeric
from crewai import Agent, Task, Crew, LLM
from dotenv import load_dotenv
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import List, Optional
from app.services.agents.travel_all_schedule_agent_service import spots_pydantic


load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AGENT_NAVER_CLIENT_ID = os.getenv("AGENT_NAVER_CLIENT_ID")
AGENT_NAVER_CLIENT_SECRET = os.getenv("AGENT_NAVER_CLIENT_SECRET")

llm = LLM(model="gpt-4o", temperature=0, api_key=OPENAI_API_KEY)

# ──────────────────────────────
# Pydantic 모델 정의
# ──────────────────────────────

class TravelPlanRequest(BaseModel):
    main_location: str = Field(..., max_length=255, description="사용자가 선택한 지역")
    start_date: str = Field(
        ..., pattern=r"\d{4}-\d{2}-\d{2}", description="여행 시작 날짜 (YYYY-MM-DD)"
    )
    end_date: str = Field(
        ..., pattern=r"\d{4}-\d{2}-\d{2}", description="여행 종료 날짜 (YYYY-MM-DD)"
    )
    ages: str = Field(..., max_length=50, description="연령대 (예: '20-30')")
    companion_count: List[int] = Field(..., description="동반자 수 목록 (예: [2, 1])")
    concepts: List[str] = Field(
        ..., description="여행 컨셉 목록 (예: ['문화', '역사'])"
    )

class spot_pydantic(BaseModel):
    kor_name: str = Field(max_length=255)
    eng_name: Optional[str] = Field(default=None, max_length=255)
    description: str = Field(max_length=255)
    address: str = Field(max_length=255)
    url: Optional[str] = Field(default=None, max_length=2083)
    image_url: str = Field(max_length=2083)
    map_url: str = Field(max_length=2083)
    latitude: float = Field(..., description="위도", example=37.5665)
    longitude: float = Field(..., description="경도", example=126.9780)
    spot_category: int
    phone_number: Optional[str] = Field(default=None, max_length=300)
    business_status: Optional[bool] = None
    business_hours: Optional[str] = Field(default=None, max_length=255)
    order: int
    day_x: int
    spot_time: Optional[str] = None


# ──────────────────────────────
# 헬퍼 함수 및 API 도구 (네이버 웹/이미지 검색 등)
# ──────────────────────────────

def check_url_openable(url: str) -> bool:
    try:
        resp = requests.head(url, allow_redirects=True, timeout=5)
        return 200 <= resp.status_code < 400
    except Exception:
        return False

def relevance_score(item_title: str, keywords: List[str]) -> int:
    title_clean = re.sub(r"<.*?>", "", item_title)
    score = 0
    for kw in keywords:
        if kw in title_clean:
            score += 1
    return score

class NaverWebSearchTool(BaseTool):
    name: str = "NaverWebSearch"
    description: str = "네이버 웹 검색 API를 사용해 관광지에 맞는 정보를 검색"

    def _run(self, query: str) -> str:
        if not AGENT_NAVER_CLIENT_ID or not AGENT_NAVER_CLIENT_SECRET:
            return "[NaverWebSearchTool] 네이버 API 자격 증명이 없습니다."
        url = "https://openapi.naver.com/v1/search/webkr.json"
        headers = {
            "X-Naver-Client-Id": AGENT_NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": AGENT_NAVER_CLIENT_SECRET,
        }
        params = {"query": query, "display": 3, "start": 1, "sort": "sim"}
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

class NaverImageSearchTool(BaseTool):
    name: str = "NaverImageSearch"
    description: str = "네이버 이미지 검색 API를 사용해 관광지에 맞는 이미지 URL을 검색"

    def _run(self, query: str) -> str:
        if not query.strip():
            return ""
        if not AGENT_NAVER_CLIENT_ID or not AGENT_NAVER_CLIENT_SECRET:
            return "[NaverImageSearchTool] 네이버 API 자격 증명이 없습니다."

        url = "https://openapi.naver.com/v1/search/image"
        headers = {
            "X-Naver-Client-Id": AGENT_NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": AGENT_NAVER_CLIENT_SECRET,
        }
        params = {
            "query": query,
            "display": 10,
            "start": 1,
            "sort": "sim",
            "filter": "all",
        }
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            if not items:
                return ""
            keywords = query.split()
            items_sorted = sorted(
                items,
                key=lambda item: relevance_score(item.get("title", ""), keywords),
                reverse=True,
            )
            valid_items = []
            for item in items_sorted:
                link = item.get("link")
                if link and "wikimedia.org" in link:
                    continue
                if link and check_url_openable(link):
                    valid_items.append(item)
            if not valid_items:
                return ""
            return valid_items[0].get("link", "")
        except Exception as e:
            return f"[NaverImageSearchTool] 에러: {str(e)}"

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

def get_image_url_for_place(query: str) -> str:
    modified_query = f"{query} 관광지"
    tool = NaverImageSearchTool()
    return tool._run(modified_query)

def add_images_to_recommendations(recommendations: list) -> list:
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_place = {
            executor.submit(
                get_image_url_for_place,
                (place.get("kor_name", "").strip() or place.get("address", "").strip()),
            ): place
            for place in recommendations
        }
        for future in concurrent.futures.as_completed(future_to_place):
            place = future_to_place[future]
            try:
                image_url = future.result()
            except Exception:
                image_url = ""
            place["image_url"] = image_url
    return recommendations

def create_tourist_plan(user_input: dict):
    """
    user_input 예시:
    {
      "main_location": "서울",
      "start_date": "2024-03-01",
      "end_date": "2024-03-03",
      "ages": "20-30",
      "companion_count": [2, 1],
      "concepts": ["문화", "역사"],
      "prompt": "좀 더 이색적인 장소 위주로 추천해줘!"   // (추가된 프롬프트, 있을 경우)
    }
    """
    try:
        # 추가 프롬프트가 있다면 추출 (있지 않으면 빈 문자열)
        extra_prompt = user_input.pop("prompt", "")

        location = user_input["main_location"]
        start_date = user_input["start_date"]
        end_date = user_input["end_date"]
        ages = user_input["ages"]
        companion_count = user_input["companion_count"]
        concepts = user_input["concepts"]

        # 추가 프롬프트가 있을 경우 goal 메시지에 반영
        extra_text = f" 추가 요청: {extra_prompt}" if extra_prompt else ""

        tourist_agent = Agent(
            role="관광지 추천 에이전트",
            goal=(
                f"사용자에게 {location} 지역에서 {start_date}부터 {end_date}까지 여행하는 여행객의 정보를 바탕으로, "
                f"연령대 {ages}, 동반자 수 {companion_count}명, 여행 컨셉 {concepts}을 고려하여 관광지 정보를 추천하라."
                f"{extra_text} "  # 추가 프롬프트 반영
                "각 관광지는 반드시 아래 JSON 객체 형식을 준수해야 하며, 다른 텍스트를 포함하지 말라.\n"
                "{\n"
                '  "kor_name": string,\n'
                '  "eng_name": string or null,\n'
                '  "description": string,\n'
                '  "address": string,\n'
                '  "url": string or null,\n'
                '  "image_url": string,\n'
                '  "map_url": string,\n'
                '  "latitude": number,\n'
                '  "longitude": number,\n'
                '  "spot_category": number,\n'
                '  "phone_number": string or null,\n'
                '  "business_status": boolean or null,\n'
                '  "business_hours": string or null,\n'
                '  "spot_time": string or null\n'
                "}"
            ),
            backstory=(
                f"나는 {location} 지역의 관광지 전문가로, 최신 정보와 데이터를 기반으로 여행객에게 최적의 관광지 추천을 제공할 수 있습니다. "
                "내 역할은 사용자의 여행 계획에 맞춰 상세하고 신뢰할 수 있는 관광 정보를 제시하는 것입니다."
            ),
            tools=[NaverWebSearchTool()],
            llm=llm,
            verbose=True,
        )

        tourist_task = Task(
            description=(
                f"'{location}' 지역의 관광지 추천을 위해 아래 요구사항을 충족하는 관광지를 최소 5곳 추천하라.\n"
                f"요구사항:\n"
                f"- 각 관광지는 위의 JSON 객체 형식을 준수할 것.\n"
                f"- 주소, 전화번호, 운영시간 등 가능한 상세 정보를 포함할 것.\n"
                f"- 'description' 필드에 추천 이유나 관광지의 특징을 간략히 설명할 것.\n"
                f"주의: 결과는 반드시 순수한 JSON 배열 형식(예: [ {{...}}, {{...}}, ... ])로 반환하고, 다른 텍스트는 포함하지 말라."
            ),
            agent=tourist_agent,
            expected_output="관광지 추천 결과 (JSON 형식)",
        )

        tasks = [tourist_task]
        crew = Crew(
            agents=[tourist_agent],
            tasks=tasks,
            verbose=True,
        )

        crew.kickoff()
        raw_output = tourist_task.output

        recommendations = extract_recommendations_from_output(raw_output)
        recommendations_with_images = add_images_to_recommendations(recommendations)

        spots_list = []
        for idx, rec in enumerate(recommendations_with_images, start=1):
            orig_map_url = rec.get("map_url", "").strip()
            if not orig_map_url or "map.naver.com" not in orig_map_url:
                longitude = rec.get("longitude", 0.0)
                latitude = rec.get("latitude", 0.0)
                map_url = (
                    f"https://map.naver.com/v5/?c={longitude},{latitude},15,0,0,0,dh"
                )
            else:
                map_url = orig_map_url

            spot = spot_pydantic(
                kor_name=rec.get("kor_name", ""),
                eng_name=rec.get("eng_name", None),
                description=rec.get("description", ""),
                address=rec.get("address", ""),
                url=rec.get("url", None),
                image_url=rec.get("image_url", ""),
                map_url=map_url,
                latitude=rec.get("latitude", 0.0),
                longitude=rec.get("longitude", 0.0),
                spot_category=rec.get("spot_category", 1),
                phone_number=rec.get("phone_number", None),
                business_status=rec.get("business_status", None),
                business_hours=rec.get("business_hours", None),
                order=idx,
                day_x=1,
                spot_time=rec.get("spot_time", None),
            )
            spots_list.append(spot)

        site_response = spots_pydantic(spots=spots_list)
        return site_response.model_dump()

    except Exception as e:
        print(f"[ERROR] {e}")
        traceback.print_exc()
        return {"message": "관광지 추천 처리 중 오류가 발생했습니다.", "error": str(e)}
