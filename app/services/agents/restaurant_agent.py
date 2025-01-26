import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
import googlemaps
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

load_dotenv()


class RestaurantRecommender:
    def __init__(self):
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.GOOGLE_MAP_API_KEY = os.getenv("GOOGLE_MAP_API_KEY")
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=self.OPENAI_API_KEY)
        self.gmaps = googlemaps.Client(key=self.GOOGLE_MAP_API_KEY)
        self._setup_chains()

    def _setup_chains(self):
        analysis_prompt = PromptTemplate.from_template(
            """
            당신은 한국의 맛집을 완벽하게 이해하고 있는 미식 전문가 AI입니다.
            사용자의 여행 정보를 분석하여 최적의 맛집 추천을 위한 키워드를 추출해주세요.

            여행 정보:
            - 위치: {location}
            - 시작일: {start_date}
            - 종료일: {end_date}
            - 컨셉: {concepts}
            
            지역 특색, 음식 종류, 분위기 등을 고려하여 핵심 키워드만 쉼표로 구분하여 출력하세요.
            """
        )

        filter_restaurants_prompt = PromptTemplate.from_template(
            """
            당신은 대한민국의 모든 맛집 정보를 가진 전문 식당 추천 AI입니다.
            아래의 식당 목록에서 평점과 리뷰 수를 기준으로 최적의 식당 리스트를 추출해주세요.

            분석된 키워드: {keywords}
            식당 목록: {restaurants}
            필요한 식사 횟수: {total_meals}

            조건:
            1. 평점과 리뷰 수를 기준으로 상위 식당을 선택하세요.
            2. 결과는 {total_meals}개의 식당으로 제한합니다.
            3. 중복된 식당은 제거하세요.

            응답 형식:
            [
                {{
                    "restaurant_id": "실제 place_id",
                    "name": "식당 이름",
                    "rating": 평점 (숫자),
                    "review_count": 리뷰 수 (숫자)
                }}
            ]
            """
        )

        recommend_meals_prompt = PromptTemplate.from_template(
            """
            당신은 대한민국의 모든 맛집 정보를 가진 전문 식당 추천 AI입니다.
            주어진 식당 리스트를 바탕으로 시간대별 최적의 식당을 추천해주세요.

            식당 리스트: {filtered_restaurants}
            식사 일정: {meals}

            조건:
            1. 아침, 점심, 저녁 각각의 시간대에 적합한 식당을 선택하세요.
            2. 각 식당은 한 번만 선택해야 합니다.
            3. 추천 이유를 간단히 포함하세요.

            응답 형식:
            [
                {{
                    "restaurant_id": "실제 place_id",
                    "meal_time": "아침/점심/저녁",
                    "day": 숫자 (1부터 시작),
                    "order": 숫자 (1부터 시작),
                    "reason": "추천 이유"
                }}
            ]
            """
        )

        details_prompt = PromptTemplate.from_template(
            """
            당신은 한국의 모든 맛집에 대한 상세 정보를 제공하는 미식 전문 AI입니다.
            
            식당 정보:
            {restaurant_info}
            식사 시간대: {meal_time}

            다음을 포함하여 한 문단으로 설명해주세요:
            - 대표 메뉴와 특징
            - {meal_time} 추천 메뉴
            - 주변 정보
            - 방문 팁
            """
        )

        self.analysis_chain = analysis_prompt | self.llm
        self.filter_restaurants_chain = filter_restaurants_prompt | self.llm
        self.recommend_meals_chain = recommend_meals_prompt | self.llm
        self.details_chain = details_prompt | self.llm

    def _calculate_meals(self, start_date: str, end_date: str) -> List[Dict[str, str]]:
        start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        days = (end - start).days + 1

        meals = []
        for day in range(1, days + 1):
            if day == 1:
                if start.hour < 10:
                    meals.append({"day": day, "meal_time": "아침"})
                meals.append({"day": day, "meal_time": "점심"})
                meals.append({"day": day, "meal_time": "저녁"})
            elif day == days:
                meals.append({"day": day, "meal_time": "아침"})
                meals.append({"day": day, "meal_time": "점심"})
            else:
                meals.append({"day": day, "meal_time": "아침"})
                meals.append({"day": day, "meal_time": "점심"})
                meals.append({"day": day, "meal_time": "저녁"})
        return meals

    def search_restaurants(self, location: str) -> List[Dict]:
        results = []
        try:
            geocode_result = self.gmaps.geocode(location)
            if not geocode_result:
                return []

            lat = geocode_result[0]["geometry"]["location"]["lat"]
            lng = geocode_result[0]["geometry"]["location"]["lng"]

            places = self.gmaps.places_nearby(
                location=(lat, lng),
                radius=1500,
                keyword="맛집",
                language="ko",
                type="restaurant",
            )
            results.extend(places.get("results", []))

            if "next_page_token" in places:
                import time

                time.sleep(2)
                next_places = self.gmaps.places_nearby(
                    location=(lat, lng),
                    page_token=places["next_page_token"],
                )
                results.extend(next_places.get("results", []))

            unique_results = {r["place_id"]: r for r in results}  # 중복 제거
            sorted_results = sorted(
                unique_results.values(),
                key=lambda x: (x.get("rating", 0), x.get("user_ratings_total", 0)),
                reverse=True,
            )
            return sorted_results[:40]

        except Exception as e:
            print(f"검색 오류: {e}")
            return []

    def process_recommendation(self, plan_data: Dict) -> Dict:
        try:
            keywords = self.analysis_chain.invoke(
                {
                    "location": plan_data["plan"]["main_location"],
                    "start_date": plan_data["plan"]["start_date"],
                    "end_date": plan_data["plan"]["end_date"],
                    "concepts": ", ".join(plan_data["plan"]["concepts"]),
                }
            ).content

            restaurants = self.search_restaurants(plan_data["plan"]["main_location"])
            meals = self._calculate_meals(
                plan_data["plan"]["start_date"], plan_data["plan"]["end_date"]
            )

            filtered_restaurants_response = self.filter_restaurants_chain.invoke(
                {
                    "keywords": keywords,
                    "restaurants": json.dumps(restaurants, ensure_ascii=False),
                    "total_meals": len(meals),
                }
            ).content

            filtered_restaurants = json.loads(
                filtered_restaurants_response.replace("```json", "")
                .replace("```", "")
                .strip()
            )

            recommendations_response = self.recommend_meals_chain.invoke(
                {
                    "filtered_restaurants": json.dumps(
                        filtered_restaurants, ensure_ascii=False
                    ),
                    "meals": json.dumps(meals, ensure_ascii=False),
                }
            ).content

            recommendations = json.loads(
                recommendations_response.replace("```json", "")
                .replace("```", "")
                .strip()
            )

            spots = []
            used_restaurants = set()
            for rec in recommendations:
                if rec["restaurant_id"] not in used_restaurants:
                    validated = self.validate_restaurant(rec["restaurant_id"], rec)
                    if validated:
                        spots.append(validated)
                        used_restaurants.add(rec["restaurant_id"])

            return {
                "data": [
                    {"plan": plan_data["plan"]},
                    {"Spots": spots},
                ]
            }
        except Exception as e:
            print(f"추천 처리 오류: {e}")
            return {"data": [{"plan": plan_data["plan"]}, {"Spots": []}]}

    def validate_restaurant(self, place_id: str, meal_info: Dict) -> Optional[Dict]:
        try:
            details = self.gmaps.place(
                place_id,
                fields=[
                    "name",
                    "formatted_address",
                    "rating",
                    "user_ratings_total",
                    "opening_hours",
                    "formatted_phone_number",
                    "website",
                    "url",
                    "geometry",
                ],
                language="ko",
            )["result"]

            if not details.get("geometry"):
                print(f"geometry 필드 누락: {place_id}")
                return None

            if details.get("rating", 0) >= 4.0:
                description = self.details_chain.invoke(
                    {
                        "restaurant_info": json.dumps(details, ensure_ascii=False),
                        "meal_time": meal_info.get("meal_time", "점심"),
                    }
                ).content

                return {
                    "kor_name": details.get("name"),
                    "eng_name": details.get("name"),
                    "description": description,
                    "address": details.get("formatted_address"),
                    "rating": details.get("rating"),
                    "review_count": details.get("user_ratings_total"),
                    "phone_number": details.get("formatted_phone_number"),
                    "website": details.get("website"),
                    "business_hours": details.get("opening_hours", {}).get(
                        "weekday_text", []
                    ),
                    "map_url": f"https://www.google.com/maps/search/?api=1&query={details['geometry']['location']['lat']},{details['geometry']['location']['lng']}",
                }
            return None
        except Exception as e:
            print(f"검증 오류: {e}")
            return None


def main():
    recommender = RestaurantRecommender()
    plan_data = {
        "plan": {
            "id": 1,
            "name": "부산 여행",
            "member_id": 0,
            "companion_count": 3,
            "main_location": "부산 해운대",
            "concepts": ["가족", "맛집"],
            "uses": 0,
            "start_date": "2025-01-26T11:00:00",
            "end_date": "2025-01-27T16:00:00",
        }
    }

    result = recommender.process_recommendation(plan_data)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
