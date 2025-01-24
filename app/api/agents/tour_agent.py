from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import os
import re
from dotenv import load_dotenv

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI

# 환경 변수 로드
load_dotenv()

app = FastAPI()

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

# ---------------------------
# 1) 사용자 조건 분석 -> 주요 테마 추출
# ---------------------------
condition_prompt = PromptTemplate(
    input_variables=["location", "days", "age_group", "purposes"],
    template="""
    당신은 여행 플래너입니다. 다음 사용자 조건을 간단히 분석하여
    주요 테마(예: 자연, 문화, 휴양, 액티비티 등)를 2~3개로 짧게 추출하세요.

    - 목적지: {location}
    - 여행일수: {days}일
    - 연령대: {age_group}
    - 여행 목적: {purposes}

    예) "자연, 문화, 액티비티"
    """
)

condition_chain = LLMChain(
    llm=ChatOpenAI(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-3.5-turbo",
        temperature=0
    ),
    prompt=condition_prompt
)

# ---------------------------
# 2) 날짜별로 "정확히 3개"씩 여행지 추천
# ---------------------------
recommendation_prompt = PromptTemplate(
    input_variables=["themes", "location", "days"],
    template="""
    다음 조건에 맞춰 {days}일 동안 매일 **정확히 3개의 여행지**를 제안해 주세요.
    - 여행지(지역): {location}
    - 테마: {themes}

    각 여행지는 한국어 이름으로만 작성하며, 아래 형식을 따르세요:

    1일차
    1. 여행지 이름
    2. 여행지 이름
    3. 여행지 이름

    2일차
    1. 여행지 이름
    2. 여행지 이름
    3. 여행지 이름

    다른 설명이나 문장은 작성하지 마세요.
    """
)

recommendation_chain = LLMChain(
    llm=ChatOpenAI(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-3.5-turbo",
        temperature=0
    ),
    prompt=recommendation_prompt
)

# ---------------------------
# 3) 여행지별 간단 상세 (1~2줄 + URL)
# ---------------------------
details_prompt = PromptTemplate(
    input_variables=["destination"],
    template="""
    아래 형식으로 {destination}에 대한 정보를 간단히 작성하세요(한국어).
    다른 문장은 절대 추가하지 마세요.

    이름: {destination}
    설명: 1~2줄로 간단히
    이미지 URL: https://phoko.visitkorea.or.kr/media/mediaList.kto?keyword={destination}
    """
)

details_chain = LLMChain(
    llm=ChatOpenAI(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-3.5-turbo",
        temperature=0
    ),
    prompt=details_prompt
)


# ---------------------------
# Helper: 부족한 여행지를 채우는 함수
# ---------------------------
def fill_missing_destinations(destinations, required_count=3):
    """
    만약 한 날짜에 3개 미만의 여행지가 나오면 "미정"으로 채워넣습니다.
    """
    default_dest = ["미정"]
    missing_count = required_count - len(destinations)
    if missing_count > 0:
        destinations += default_dest * missing_count
        destinations = destinations[:required_count]  # 정확히 3개만
    return destinations


@app.post("/recommendations/", response_model=List[Recommendation])
async def get_recommendations(user_input: UserInput):
    """
    1) 사용자 입력을 받아 테마를 추출
    2) 날짜별 3개씩 여행지 목록을 생성
    3) 각 여행지에 대해 상세정보(1~2줄+URL)를 생성
    4) 최종 결과를 Recommendation 리스트로 반환
    """
    try:
        # 1) 사용자 조건 분석 -> 테마
        purpose_str = ", ".join(user_input.purposes)
        condition_summary = condition_chain.run({
            "location": user_input.location,
            "days": user_input.days,
            "age_group": user_input.age_group,
            "purposes": purpose_str
        })
        themes = condition_summary.strip()
        

        # 2) 날짜별 여행지 추천
        raw_recommendations = recommendation_chain.run({
            "themes": themes,
            "location": user_input.location,
            "days": user_input.days
        })
        

        # ----------------------------
        # 줄 단위로 파싱: "N일차" 라인을 만나면 day = N
        #               "숫자. 장소" 라인을 만나면 해당 day에 장소 추가
        # ----------------------------
        lines = raw_recommendations.split("\n")
        current_day = 0
        day_destinations_map = dict()

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue  # 빈 줄은 무시

            # N일차 -> day 설정
            m_day = re.match(r"^(\d+)일차$", line_str)
            if m_day:
                current_day = int(m_day.group(1))
                day_destinations_map[current_day] = []
                
                continue

            # "숫자. 장소" 형식 -> parse
            m_place = re.match(r"^(\d+)\.\s*(.*)$", line_str)
            if m_place:
                dest_name = m_place.group(2).strip()
                
                if current_day not in day_destinations_map:
                    day_destinations_map[current_day] = []
                day_destinations_map[current_day].append(dest_name)
                continue

            

        # 이제 day_destinations_map에 날짜별 여행지 리스트가 있다.
        # 3) 각 날짜별 3개 미만이면 채우고, details_chain 호출
        detailed_recommendations: List[Recommendation] = []
        for day_num in range(1, user_input.days + 1):
            day_list = day_destinations_map.get(day_num, [])
            day_list = fill_missing_destinations(day_list)

            order = 1
            for place in day_list:
                if place == "미정":
                    # 미정 데이터면 바로 기본값
                    detailed_recommendations.append(Recommendation(
                        picture_url="https://via.placeholder.com/300",
                        name="미정",
                        description="정보를 가져오는 데 실패했습니다.",
                        order=order,
                        day=day_num
                    ))
                else:
                    try:
                        
                        detail_text = details_chain.run({"destination": place})
                        
                    except Exception as e:
                        
                        detail_text = (
                            f"이름: {place}\n"
                            "설명: 정보를 가져오는 데 실패했습니다.\n"
                            "이미지 URL: https://via.placeholder.com/300"
                        )

                    # 파싱
                    lines_detail = detail_text.split("\n")
                    name_line = next(
                        (l.split(": ", 1)[-1].strip() for l in lines_detail if l.startswith("이름:")),
                        place
                    )
                    desc_line = next(
                        (l.split(": ", 1)[-1].strip() for l in lines_detail if l.startswith("설명:")),
                        "정보 없음"
                    )
                    url_line = next(
                        (l.split(": ", 1)[-1].strip() for l in lines_detail if l.startswith("이미지 URL:")),
                        "https://via.placeholder.com/300"
                    )

                    detailed_recommendations.append(Recommendation(
                        picture_url=url_line,
                        name=name_line,
                        description=desc_line,
                        order=order,
                        day=day_num
                    ))
                order += 1

        return detailed_recommendations

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")


@app.get("/test-recommendations/")
async def test_recommendations():
    return [
        {
            "day": 1,
            "places": [
                {
                    "name": "Test Place 1",
                    "description": "A sample description.",
                    "image_url": "https://example.com/image1.jpg",
                    "order": 1
                },
                {
                    "name": "Test Place 2",
                    "description": "Another sample description.",
                    "image_url": "https://example.com/image2.jpg",
                    "order": 2
                }
            ]
        }
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
