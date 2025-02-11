import traceback
import os
from dotenv import load_dotenv
import asyncio

from crewai import Agent, Task, Crew, LLM
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import List, Optional
from app.dtos.spot_models import spot_pydantic, spots_pydantic
from app.services.agents.site_tool import (
    NaverWebSearchTool,
    extract_recommendations_from_output,
    add_images_to_recommendations,
    get_lat_lon_for_place_kakao,  # 카카오 API 함수 임포트
)

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# LLM 초기화
llm = LLM(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY)


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
    prompt: Optional[str] = Field(default="", description="추가 요청 프롬프트")


class TravelPlanAgentService:
    """
    여행 추천 에이전트를 싱글톤 패턴으로 관리하는 서비스 클래스
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TravelPlanAgentService, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        """에이전트와 필요한 도구 초기화"""
        self.llm = llm
        self.naver_web_tool = NaverWebSearchTool()

        self.tourist_agent = Agent(
            role="관광지 추천 에이전트",
            goal=(
                "사용자에게 특정 지역에서 여행하는 여행객의 정보를 바탕으로, "
                "해당 지역의 관광지 정보를 추천하라. 각 관광지는 반드시 아래 JSON 객체 형식을 준수해야 하며, "
                "다른 텍스트를 포함하지 말라.\n"
                "{\n"
                '  "kor_name": string,\n'
                '  "eng_name": string or null,\n'
                '  "address": string,\n'
                '  "url": string or null,\n'
                '  "image_url": string,\n'
                '  "map_url": string,\n'
                '  "spot_category": number,\n'
                '  "phone_number": string or null,\n'
                '  "business_status": boolean or null,\n'
                '  "business_hours": string or null,\n'
                '  "spot_time": string or null\n'
                "}"
            ),
            backstory=(
                "나는 특정 지역의 관광지 전문가로 최신 정보와 데이터를 기반으로 여행객에게 최적의 관광지 추천을 제공할 수 있습니다. "
                "내 역할은 사용자의 여행 계획에 맞춰 상세하고 신뢰할 수 있는 관광 정보를 제시하는 것입니다."
            ),
            tools=[self.naver_web_tool],
            llm=self.llm,
            verbose=True,
        )

    async def create_tourist_plan(self, user_input: dict):
        """
        여행 추천 계획을 생성하는 비동기 메서드.

        user_input 예시:
        {
          "main_location": "부산",
          "start_date": "2024-03-01",
          "end_date": "2024-03-03",
          "ages": "20-30",
          "companion_count": [2, 1],
          "concepts": ["문화", "역사"],
          "prompt": "다른 관광지 추천해줘!"
        }
        """
        try:
            extra_prompt = user_input.pop("prompt", "")
            location = user_input[
                "main_location"
            ]  # 원래 사용자가 입력한 지역 (예: 부산)
            start_date = user_input["start_date"]
            end_date = user_input["end_date"]
            ages = user_input["ages"]
            companion_count = user_input["companion_count"]
            concepts = user_input["concepts"]

            extra_text = f" 추가 요청: {extra_prompt}" if extra_prompt else ""

            # 에이전트의 목표(goal)는 원래의 main_location (예: 부산)을 그대로 사용하고,
            # 프롬프트가 있으면 추가 요청으로 반영합니다.
            self.tourist_agent.goal = (
                f"사용자에게 {location} 지역에서 {start_date}부터 {end_date}까지 여행하는 여행객의 정보를 바탕으로, "
                f"연령대 {ages}, 동반자 수 {companion_count}명, 여행 컨셉 {concepts}을 고려하여 관광지 정보를 추천하라. "
                f"추천은 반드시 사용자가 처음에 입력한 지역인 {location}을 기준으로 해야 하며, 다른 지역으로 변경하지 말 것. "
                "각 관광지는 반드시 아래 JSON 객체 형식을 준수해야 하며, 다른 텍스트는 포함하지 말라.\n"
                "{\n"
                '  "kor_name": string,\n'
                '  "eng_name": string or null,\n'
                '  "address": string,\n'
                '  "url": string or null,\n'
                '  "image_url": string,\n'
                '  "map_url": string,\n'
                '  "spot_category": number,\n'
                '  "phone_number": string or null,\n'
                '  "business_status": boolean or null,\n'
                '  "business_hours": string or null,\n'
                '  "spot_time": string or null\n'
                "}"
            )

            tourist_task = Task(
                description=(
                    f"'{location}' 지역의 관광지 추천을 위해 아래 요구사항을 충족하는 관광지를 최소 5곳 추천하라.\n"
                    "요구사항:\n"
                    "- 각 관광지는 위의 JSON 객체 형식을 준수할 것.\n"
                    "- 주소, 전화번호, 운영시간 등 가능한 상세 정보를 포함할 것.\n"
                    "- 'description' 필드에 추천 이유나 관광지의 특징을 간략히 설명할 것.\n"
                    "주의: 결과는 반드시 순수한 JSON 배열 형식(예: [ {...}, {...}, ... ])로 반환하고, 다른 텍스트는 포함하지 말라."
                ),
                agent=self.tourist_agent,
                expected_output="관광지 추천 결과 (JSON 형식)",
            )

            tasks = [tourist_task]
            crew = Crew(
                agents=[self.tourist_agent],
                tasks=tasks,
                verbose=True,
            )

            await crew.kickoff_async()
            raw_output = tourist_task.output

            recommendations = extract_recommendations_from_output(raw_output)
            recommendations_with_images = await add_images_to_recommendations(
                recommendations
            )

            spots_list = []
            for idx, rec in enumerate(recommendations_with_images, start=1):
                orig_map_url = rec.get("map_url", "").strip()
                # 만약 응답에 위도, 경도 정보가 없거나 map_url에 네이버 맵 URL이 있다면,
                # 카카오 API를 사용하여 주소 기반 좌표 조회 후 카카오 지도 링크 생성
                if (
                    not rec.get("latitude")
                    or not rec.get("longitude")
                    or "map.naver.com" in orig_map_url
                ):
                    latitude, longitude = await get_lat_lon_for_place_kakao(
                        rec.get("address", "")
                    )
                    map_url = f"https://map.kakao.com/link/map/{rec.get('kor_name', '')},{latitude},{longitude}"
                else:
                    latitude = rec.get("latitude", 0.0)
                    longitude = rec.get("longitude", 0.0)
                    map_url = (
                        orig_map_url
                        if orig_map_url
                        else f"https://map.kakao.com/link/map/{rec.get('kor_name', '')},{latitude},{longitude}"
                    )

                spot = spot_pydantic(
                    kor_name=rec.get("kor_name", ""),
                    eng_name=rec.get("eng_name", None),
                    address=rec.get("address", ""),
                    url=rec.get("url", None),
                    image_url=rec.get("image_url", ""),
                    map_url=map_url,
                    spot_category=rec.get("spot_category", 1),
                    phone_number=rec.get("phone_number", None),
                    business_status=rec.get("business_status", None),
                    business_hours=rec.get("business_hours", None),
                    order=idx,
                    day_x=1,
                    spot_time=rec.get("spot_time", None),
                    latitude=latitude,
                    longitude=longitude,
                )
                spots_list.append(spot)

            site_response = spots_pydantic(spots=spots_list)
            return site_response.model_dump()

        except Exception as e:
            print(f"[ERROR] {e}")
            traceback.print_exc()
            return {
                "message": "관광지 추천 처리 중 오류가 발생했습니다.",
                "error": str(e),
            }
