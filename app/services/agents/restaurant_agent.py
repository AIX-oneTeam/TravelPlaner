import os
from dotenv import load_dotenv
import requests
from langchain.agents import AgentExecutor
from langchain_openai import ChatOpenAI
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain.schema.messages import SystemMessage
from langchain.agents import create_openai_functions_agent
from langchain.tools import BaseTool
from typing import Dict, List, Type
from pydantic import BaseModel
import json
from datetime import datetime, timedelta


# Tool의 입력 스키마 정의
class TravelPlan(BaseModel):
    main_location: str
    start_date: str
    end_date: str
    companion_count: int
    concepts: List[str]

# 좌표 얻어오는 함수(Google Maps Geocoding API)
def get_coordinates(location, google_maps_api_key):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": location, "key": google_maps_api_key}

    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data["results"]:
            location_data = data["results"][0]["geometry"]["location"]
            latitude = location_data["lat"]
            longitude = location_data["lng"]
            return f"{latitude},{longitude}"
    return ""


class RestaurantSearchTool(BaseTool):
    name: str = "restaurant_search"
    description: str = (
        "Searches for restaurants in the specified location. "
        "Input should be a travel plan with main_location, dates, and other details."
    )
    args_schema: Type[BaseModel] = TravelPlan

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, serpapi_key: str, google_maps_api_key: str):
        super().__init__()
        self._serpapi_key = serpapi_key
        self._google_maps_api_key = google_maps_api_key

    @property
    def serpapi_key(self) -> str:
        return self._serpapi_key

    @property
    def google_maps_api_key(self) -> str:
        return self._google_maps_api_key

    def _run(self, **kwargs) -> List[Dict]:
        """
        1) TravelPlan 정보를 받아서
        2) SerpAPI로 맛집 후보를 여러 개(최대 40개) 수집
        3) 평점 >= 4.0, 리뷰 >= 500 조건을 통과한 식당만 필터링
        4) 중복(같은 이름/주소) 제거
        5) 필터링된 전체 리스트를 반환
        """
        travel_plan = TravelPlan(**kwargs)
        location = travel_plan.main_location
        coordinates = get_coordinates(location, self.google_maps_api_key)

        if not coordinates:
            raise Exception(
                "Error: Unable to retrieve coordinates for the given location."
            )

        url = "https://serpapi.com/search"

        # 후보 식당들을 담을 리스트
        all_candidates = []

        # 중복 제거를 위한 세트
        seen_restaurants = set()

        # SerpAPI에서 최대 40개 결과( start=0, start=20 )를 가져옴
        for start in [0, 20]:
            params = {
                "engine": "google_maps",
                "q": f"{location} 맛집",
                "ll": f"@{coordinates},14z",
                "hl": "ko",
                "gl": "kr",
                "api_key": self.serpapi_key,
                "start": start,
            }

            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                results = data.get("local_results", [])

                for result in results:
                    # 평점 & 리뷰 수
                    rating = float(result.get("rating", 0))
                    reviews = int(result.get("reviews", 0))

                    # 중복 체크용 키
                    unique_key = (
                        f"{result.get('title', '')}_{result.get('address', '')}"
                    )

                    if (
                        rating >= 4.0
                        and reviews >= 500
                        and unique_key not in seen_restaurants
                    ):
                        # 후보 식당 정보 구성
                        restaurant = {
                            "kor_name": result.get("title", ""),
                            "eng_name": (
                                result.get("title", "")
                                .encode("ascii", "ignore")
                                .decode()
                            ),
                            "description": "",
                            "address": result.get("address", ""),
                            "zip": "",
                            "url": result.get("website", ""),
                            "image_url": result.get("thumbnail", ""),
                            "map_url": f"https://www.google.com/maps/place/?q=place_id:{result.get('place_id')}",
                            "likes": reviews,
                            "satisfaction": rating,
                            "spot_category": 1,
                            "phone_number": result.get("phone", ""),
                            "business_status": True,
                            "business_hours": result.get("hours", ""),
                            # day_x, order, spot_time 등은 LLM이 결정하도록 여기서는 제외
                        }

                        all_candidates.append(restaurant)
                        seen_restaurants.add(unique_key)

            else:
                raise Exception(f"Error: {response.status_code}, {response.text}")

        # 이제 all_candidates는 조건을 통과한 식당들의 전체 목록
        return all_candidates


def create_travel_agent(
    openai_api_key: str, serpapi_key: str, google_maps_api_key: str
):
    """
    - LLM(ChatOpenAI) + RestaurantSearchTool로 구성된 에이전트를 생성합니다.
    - system_prompt에서 '후보 리스트를 보고 직접 판단해 달라' + '하루 3끼씩 총 6곳을 꼭 추천해라'라고 명시적으로 지시합니다.
    - JSON 이외의 텍스트가 있으면 안 된다고 강하게 강조합니다.
    """
    llm = ChatOpenAI(temperature=0.7, api_key=openai_api_key, model="gpt-3.5-turbo")

    # 수정된 RestaurantSearchTool (평점/리뷰수 필터 + 중복 제거까지만 수행)
    restaurant_tool = RestaurantSearchTool(serpapi_key, google_maps_api_key)
    tools = [restaurant_tool]

    # 시스템 프롬프트(아래)를 매우 엄격하게 작성하여, JSON 형식을 어기지 못하게 합니다.
    system_prompt = """당신은 여행객들을 위한 맛집 추천 전문가이자, JSON 생성기입니다.
절대로 JSON 형식 이외의 텍스트를 출력하지 마세요. 
특히 "안녕하세요", "추천 리스트는 다음과 같습니다" 같은 문구는 절대 넣지 말고, 
오직 아래 형식의 JSON 하나만 결과로 내놓으세요.

1박 2일 여행이면 총 2일이므로, 하루에 3곳씩(아침, 점심, 저녁) 해서 총 6곳을 선정해야 합니다.
만약 후보가 6곳 미만이라면 나머지를 "적합한 후보가 부족합니다" 등으로 처리하세요.

아래 형식에 맞춰서 반드시 출력해야 합니다 (JSON 시작 전후로 추가 문구 금지):

{
  "Spots": [
    {
      "kor_name": "string",
      "eng_name": "string",
      "description": "string",
      "address": "string",
      "zip": "string",
      "url": "string",
      "image_url": "string",
      "map_url": "string",
      "likes": 0,
      "satisfaction": 0,
      "spot_category": 0,
      "phone_number": "string",
      "business_status": true,
      "business_hours": "string",
      "day_x": 0,
      "order": 0,
      "spot_time": "2025-02-01T09:00:00"
    }
  ]
}

- Spots 배열의 길이는 6이어야 합니다(2일 × 3곳).
- day_x: 1 또는 2
- order: 1, 2, 3
- spot_time: ISO 8601 형식 "YYYY-MM-DDTHH:mm:ss"
- 반드시 RestaurantSearchTool로부터 받은 후보 중에서만 골라야 합니다.
- 후보가 6개 미만이라면 남은 객체들을 "reason": "적합한 후보가 부족합니다" 같은 식으로 설명을 넣으세요 (그러나 JSON 필드는 위와 동일하게 유지).

예시 여행 계획:
- main_location: 부산광역시
- start_date: 2025-02-01T00:00:00
- end_date: 2025-02-02T00:00:00
- companion_count: 3
- concepts: ['가족', '맛집']

이 모든 조건을 지키지 않으면 잘못된 답변입니다. 오직 JSON만 정확히 출력하세요.
"""

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            # 사용자의 질문(휴먼 메시지)
            HumanMessagePromptTemplate.from_template("{input}"),
            # 내부 추론 메시지(Agent Scratchpad)
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    # create_openai_functions_agent: OpenAI의 Functions 기능을 활용한 에이전트
    agent = create_openai_functions_agent(llm, tools, prompt)

    # AgentExecutor를 반환
    return AgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=tools,
        verbose=True,  # 내부 동작(생각 과정) 디버그 로그 노출
        max_iterations=3,  # 반복 횟수 제한
    )


if __name__ == "__main__":
    load_dotenv()

    openai_api_key = os.getenv("OPENAI_API_KEY")
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    google_maps_api_key = os.getenv("GOOGLE_MAP_API_KEY")

    # 테스트용 여행 계획
    test_plan = {
        "id": 1,
        "name": "부산 여행",
        "member_id": 0,
        "companion_count": 3,
        "main_location": "부산광역시",
        "concepts": ["가족", "맛집"],
        "uses": 0,
        "start_date": "2025-02-01T00:00:00",
        "end_date": "2025-02-02T00:00:00",
    }

    try:
        # 에이전트 생성
        agent = create_travel_agent(openai_api_key, serpapi_key, google_maps_api_key)

        # LangChain에 들어갈 "input" (휴먼 메시지) 구성
        input_data = {
            "input": f"""
            여행 계획에 맞는 맛집을 검색해주세요.
            main_location: {test_plan['main_location']}
            start_date: {test_plan['start_date']}
            end_date: {test_plan['end_date']}
            companion_count: {test_plan['companion_count']}
            concepts: {test_plan['concepts']}
            """,
            "agent_scratchpad": "",
        }

        # 에이전트 실행
        result = agent.invoke(input_data)

        # 결과가 {"Spots": [...]} 형태인지 체크
        if isinstance(result, dict) and "Spots" not in result:
            # 혹시 "Spots"가 없으면 맞춰줌
            result = {"Spots": result.get("output", [])}

        # JSON 예쁘게 출력
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        print(f"An error occurred: {e}")
