from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import os
import re
import asyncio
from dotenv import load_dotenv

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI

# 환경 변수 로드
load_dotenv()

app = FastAPI()

# 모델 정의
class UserInput(BaseModel):
    location: str
    date: str
    days: int
    age_group: str
    companions: Dict[str, int]
    purposes: List[str]

class Recommendation(BaseModel):
    picture_url: str
    name: str
    description: str
    order: int
    day: int

# ------------------------------------------------------------------------------
# 프롬프트 정의
# ------------------------------------------------------------------------------
# 1. 주요 여행 테마 추출
condition_prompt = PromptTemplate(
    input_variables=["location", "days", "age_group", "purposes"],
    template="""
당신은 여행 플래너입니다. 아래 사용자 정보를 분석하여 주요 여행 테마 2~3개를 추출하세요 (예: 자연, 문화, 휴양, 액티비티). 추가 설명 없이 테마만 출력하세요.

- 여행지: {location}
- 여행 일수: {days}일
- 연령대: {age_group}
- 여행 목적: {purposes}

출력 예시:
"자연, 문화, 액티비티"
    """
)

# 2. 여행지 추천
recommendation_prompt = PromptTemplate(
    input_variables=["themes", "location", "days"],
    template="""
당신은 전문 여행 플래너입니다. 사용자가 {location}을(를) {days}일 동안 방문하고 싶어 합니다. 주요 테마는 {themes}입니다.

아래 형식으로 각 날짜별로 정확히 3개의 여행지를 추천하세요. 한국어로만 답변하세요:

1일차
1. 장소
2. 장소
3. 장소

2일차
1. 장소
2. 장소
3. 장소

주의사항:
1. 실제로 존재하고 잘 알려진 장소를 우선 추천하세요.
2. 잘 알려지지 않은 흥미로운 장소도 포함할 수 있습니다.
3. 확실하지 않은 경우 "장소 정보를 찾기 어렵습니다"라고 작성하세요.
4. 추가 설명은 생략하고 장소만 나열하세요.
    """
)

# 3. 여행지 세부 정보
details_prompt = PromptTemplate(
    input_variables=["destination"],
    template="""
당신은 현지 관광 가이드입니다. "{destination}"에 대한 간단한 정보를 제공하세요. 아래 형식을 따르세요:

이름: {destination}
설명: 장소에 대한 간단한 설명 (1~2문장)
이미지 URL: 실제 유효한 링크 (또는 예시 링크)

만약 장소가 가상의 장소이거나 확인할 수 없다면, "존재하지 않는 장소"라고 답변하세요.
    """
)

# ------------------------------------------------------------------------------
# LangChain 체인 정의
# ------------------------------------------------------------------------------
# LLM 인스턴스
llm = ChatOpenAI(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o-mini",
    temperature=0
)

# 체인 정의
condition_chain = LLMChain(llm=llm, prompt=condition_prompt)
recommendation_chain = LLMChain(llm=llm, prompt=recommendation_prompt)
details_chain = LLMChain(llm=llm, prompt=details_prompt)

# ------------------------------------------------------------------------------
# Helper: 부족한 여행지 채우기 (최소 3개)
# ------------------------------------------------------------------------------
def fill_missing_destinations(destinations, required_count=3):
    default_dest = ["미정"]
    missing_count = required_count - len(destinations)
    if missing_count > 0:
        destinations += default_dest * missing_count
        destinations = destinations[:required_count]
    return destinations

# Helper: 이미지 URL 검증
def validate_image_url(url: str) -> str:
    if url.startswith("http") and "." in url:
        return url
    return "https://via.placeholder.com/300"

# ------------------------------------------------------------------------------
# 메인 /recommendations 엔드포인트
# ------------------------------------------------------------------------------
@app.post("/recommendations/", response_model=List[Recommendation])
async def get_recommendations(user_input: UserInput):
    try:
        # Step 1: 주요 테마 추출
        purpose_str = ", ".join(user_input.purposes)
        condition_summary = await asyncio.to_thread(
            condition_chain.run, {
                "location": user_input.location,
                "days": user_input.days,
                "age_group": user_input.age_group,
                "purposes": purpose_str
            }
        )
        themes = condition_summary.strip()

        # Step 2: 여행지 추천
        raw_recommendations = await asyncio.to_thread(
            recommendation_chain.run, {
                "themes": themes,
                "location": user_input.location,
                "days": user_input.days
            }
        )

        # 여행지 추천 결과 파싱
        lines = raw_recommendations.split("\n")
        current_day = 0
        day_destinations_map = {}

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # "1일차" 매칭
            m_day = re.match(r"^(\d+)일차$", line_str)
            if m_day:
                current_day = int(m_day.group(1))
                day_destinations_map[current_day] = []
                continue

            # "1. 장소" 매칭
            m_place = re.match(r"^(\d+)\.\s*(.*)$", line_str)
            if m_place:
                place_name = m_place.group(2).strip()
                day_destinations_map[current_day].append(place_name)

        # Step 3: 여행지 세부 정보 가져오기
        detailed_recommendations = []

        async def get_details_for_place(place, day, order):
            if place == "미정":
                return Recommendation(
                    picture_url="https://via.placeholder.com/300",
                    name="미정",
                    description="정보를 가져오는 데 실패했습니다.",
                    order=order,
                    day=day
                )
            try:
                detail_text = await details_chain.arun({"destination": place})
                if "존재하지 않는 장소" in detail_text:
                    return Recommendation(
                        picture_url="https://via.placeholder.com/300",
                        name=place,
                        description="존재하지 않는 장소로 확인되었습니다.",
                        order=order,
                        day=day
                    )
                else:
                    lines = detail_text.split("\n")
                    name = next((l.split(":")[1].strip() for l in lines if l.startswith("이름:")), place)
                    description = next((l.split(":")[1].strip() for l in lines if l.startswith("설명:")), "정보 없음")

                    # 이미지 URL 검증
                    url_line = next((l.split(":")[1].strip() for l in lines if l.startswith("이미지 URL:")), "https://via.placeholder.com/300")
                    picture_url = validate_image_url(url_line)

                    return Recommendation(
                        picture_url=picture_url,
                        name=name,
                        description=description,
                        order=order,
                        day=day
                    )
            except Exception:
                return Recommendation(
                    picture_url="https://via.placeholder.com/300",
                    name=place,
                    description="정보를 가져오는 데 실패했습니다.",
                    order=order,
                    day=day
                )

        for day, places in day_destinations_map.items():
            places = fill_missing_destinations(places)
            tasks = [get_details_for_place(place, day, order) for order, place in enumerate(places, start=1)]
            detailed_recommendations.extend(await asyncio.gather(*tasks))

        # 유효한 추천만 필터링
        valid_recommendations = [rec for rec in detailed_recommendations if rec.name != "미정"]

        return valid_recommendations

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 생성 중 오류가 발생했습니다: {str(e)}")

# ------------------------------------------------------------------------------
# 테스트 엔드포인트
# ------------------------------------------------------------------------------
@app.get("/test-recommendations/")
async def test_recommendations():
    return [
        {
            "day": 1,
            "places": [
                {
                    "name": "테스트 장소 1",
                    "description": "샘플 설명입니다.",
                    "image_url": "https://example.com/image1.jpg",
                    "order": 1
                },
                {
                    "name": "테스트 장소 2",
                    "description": "다른 샘플 설명입니다.",
                    "image_url": "https://example.com/image2.jpg",
                    "order": 2
                }
            ]
        }
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
