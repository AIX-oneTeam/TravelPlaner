import os
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOpenAI
import requests
import json

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NAVER_SEARCH_CLIENT_ID = os.getenv("NAVER_SEARCH_CLIENT_ID")
NAVER_SEARCH_CLIENT_SECRET = os.getenv("NAVER_SEARCH_CLIENT_SECRET")

llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=OPENAI_API_KEY)


def search_naver_places(query, display=5):
    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": NAVER_SEARCH_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_SEARCH_CLIENT_SECRET,
    }
    params = {"query": query, "display": display}

    response = requests.get(url, headers=headers, params=params)
    return response.json() if response.status_code == 200 else None


def generate_restaurant_recommendations(keywords):
    restaurants_data = []

    search_query = f"{keywords['location']} 맛집"
    places_data = search_naver_places(search_query)

    if places_data and "items" in places_data:
        restaurants_data = places_data["items"]

    user_data_description = f"""
    당신은 대한민국에 있는 식당에 대한 전문가이자 추천 AI입니다. 사용자의 여행 데이터를 기반으로 여행 일정에 가장 적합한 식당을 추천해주세요.

    여행 계획 데이터:
    - 위치: {keywords['location']}
    - 여행 날짜: {keywords['dates']}
    - 연령대: {keywords['age_group']}
    - 그룹 구성: 성인 {keywords['group']['adults']}, 아동 {keywords['group']['children']}, 반려동물 {keywords['group']['pets']}
    - 여행 테마: {', '.join(keywords['themes'])}

    실제 식당 데이터:
    {json.dumps(restaurants_data, ensure_ascii=False, indent=2)}

    위 실제 식당 데이터를 기반으로 {keywords['location']} 지역의 식당을 추천해주세요.
    제공된 실제 식당 정보만 사용하여 추천해주세요.

    추천 일정 규칙:
    - 전체 여행일(1월 22일~24일)은 하루 3끼(아침, 점심, 저녁) 추천
    - 마지막 여행일(1월 25일)은 2끼(아침, 점심) 추천

    다음과 같은 JSON 형식으로 응답해주세요:
    {{
        "recommendations": [
            {{
                "day": "1일차",
                "order": "1",
                "name": "식당명",
                "description": "식당 설명",
                "address": "주소",
                "category": "음식 종류",
                "reason": "추천 이유",
                "place_description": "장소 상세 설명"
            }}
        ]
    }}
    """

    try:
        response = llm.predict(user_data_description)
        return response.strip()
    except Exception as e:
        print(f"GPT 호출 오류: {e}")
        return "추천 실패: GPT 호출 중 문제가 발생했습니다."


keywords = {
    "location": "부산 해운대",
    "dates": "2025년 1월 22일 ~ 2025년 1월 25일",
    "age_group": "10대 미만",
    "themes": ["가족 여행", "리조트"],
    "group": {"adults": 2, "children": 1, "pets": 1},
}

recommendation = generate_restaurant_recommendations(keywords)
print("\n=== 추천 맛집 ===")
print(recommendation)
