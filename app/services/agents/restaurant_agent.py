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
        "Searches for restaurants in the specified location. Input should be a travel plan with main_location, dates, and other details."
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
        travel_plan = TravelPlan(**kwargs)
        location = travel_plan.main_location
        coordinates = get_coordinates(location, self.google_maps_api_key)

        if not coordinates:
            raise Exception(
                "Error: Unable to retrieve coordinates for the given location."
            )

        url = "https://serpapi.com/search"
        all_restaurants = []
        seen_restaurants = set()

        # 여행 일정에 맞는 일수 계산 (종료 날짜 - 시작 날짜)
        start_date = datetime.strptime(travel_plan.start_date, "%Y-%m-%dT%H:%M:%S")
        end_date = datetime.strptime(travel_plan.end_date, "%Y-%m-%dT%H:%M:%S")
        num_days = (end_date - start_date).days + 1

        daily_recommendations = {day: [] for day in range(1, num_days + 1)}
        daily_meal_times = ["아침", "점심", "저녁"]

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
                    unique_key = (
                        f"{result.get('title', '')}_{result.get('address', '')}"
                    )
                    if (
                        result.get("rating", 0) >= 4
                        and result.get("reviews", 0) >= 500
                        and unique_key not in seen_restaurants
                    ):
                        for day in range(1, num_days + 1):
                            if len(daily_recommendations[day]) < len(daily_meal_times):
                                restaurant = {
                                    "kor_name": result.get("title", ""),
                                    "eng_name": result.get("title", "")
                                    .encode("ascii", "ignore")
                                    .decode(),
                                    "description": "",
                                    "address": result.get("address", ""),
                                    "zip": "",
                                    "url": result.get("website", ""),
                                    "image_url": result.get("thumbnail", ""),
                                    "map_url": f"https://www.google.com/maps/place/?q=place_id:{result.get('place_id')}",
                                    "likes": result.get("reviews", 0),
                                    "satisfaction": float(result.get("rating", 0)),
                                    "spot_category": 1,
                                    "phone_number": result.get("phone", ""),
                                    "business_status": True,
                                    "business_hours": result.get("hours", ""),
                                    "order": len(daily_recommendations[day]) + 1,
                                    "day_x": day,
                                    "spot_time": daily_meal_times[
                                        len(daily_recommendations[day])
                                    ],
                                }
                                daily_recommendations[day].append(restaurant)
                                seen_restaurants.add(unique_key)
                                break
            else:
                raise Exception(f"Error: {response.status_code}, {response.text}")

        sorted_recommendations = [
            restaurant
            for day in range(1, num_days + 1)
            for restaurant in daily_recommendations[day]
        ]
        return sorted_recommendations


def create_travel_agent(
    openai_api_key: str, serpapi_key: str, google_maps_api_key: str
):
    llm = ChatOpenAI(temperature=0.7, api_key=openai_api_key, model="gpt-3.5-turbo")
    restaurant_tool = RestaurantSearchTool(serpapi_key, google_maps_api_key)

    tools = [restaurant_tool]

    system_prompt = """당신은 여행객들을 위한 맛집 추천 전문가입니다. 주어진 여행 정보와 맛집 리스트를 기반으로 최적의 맛집을 추천해주세요.
    반드시 다음과 같은 JSON 형식으로 출력해야 합니다:
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
          "order": 0,
          "day_x": 0,
          "spot_time": "06:27:43.593Z"
        }
      ]
    }

    각 맛집에 대해 다음을 고려하여 정보를 채워주세요:
    1. 상세한 설명과 추천 이유를 description에 작성
    2. 여행 일자별로 day_x 지정 (첫날=1)
    3. 각 날짜별 방문 순서를 order로 지정
    4. 방문하기 좋은 시간을 ISO 8601 형식으로 spot_time에 지정
    5. 모든 필드는 반드시 포함되어야 합니다."""

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            HumanMessagePromptTemplate.from_template("{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_openai_functions_agent(llm, tools, prompt)

    return AgentExecutor.from_agent_and_tools(
        agent=agent, tools=tools, verbose=True, max_iterations=3
    )


if __name__ == "__main__":
    load_dotenv()

    openai_api_key = os.getenv("OPENAI_API_KEY")
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    google_maps_api_key = os.getenv("GOOGLE_MAP_API_KEY")

    test_plan = {
        "id": 1,
        "name": "부산 여행",
        "member_id": 0,
        "companion_count": 3,
        "main_location": "부산광역시",
        "concepts": ["가족", "맛집"],
        "uses": 0,
        "start_date": "2025-02-01T11:00:00",
        "end_date": "2025-02-03T16:00:00",
    }

    try:
        agent = create_travel_agent(openai_api_key, serpapi_key, google_maps_api_key)

        input_data = {
            "input": f"""
            여행 계획에 맞는 맛집을 검색해주세요:
            main_location: {test_plan['main_location']}
            start_date: {test_plan['start_date']}
            end_date: {test_plan['end_date']}
            companion_count: {test_plan['companion_count']}
            concepts: {test_plan['concepts']}
            """,
            "agent_scratchpad": "",
        }

        result = agent.invoke(input_data)
        if isinstance(result, dict) and "Spots" not in result:
            result = {"Spots": result.get("output", [])}
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"An error occurred: {e}")
