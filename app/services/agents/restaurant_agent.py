import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
import googlemaps
import json
from datetime import datetime
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
        analysis_prompt = PromptTemplate.from_template("""
        당신은 한국의 맛집을 완벽하게 이해하고 있는 미식 전문가 AI입니다.
        사용자의 여행 정보를 분석하여 최적의 맛집 추천을 위한 키워드를 추출해주세요.

        여행 정보:
        - 위치: {location}
        - 시작일: {start_date}
        - 종료일: {end_date}
        - 컨셉: {concepts}
        
        지역 특색, 음식 종류, 분위기 등을 고려하여 핵심 키워드만 쉼표로 구분하여 출력하세요.
        """)

        recommendation_prompt = PromptTemplate.from_template("""
        당신은 대한민국의 모든 맛집 정보를 가진 전문 식당 추천 AI입니다.
        주어진 정보를 바탕으로 최적의 맛집을 추천해주세요.

        분석된 키워드: {keywords}
        필요한 식사 횟수: {total_meals}회
        식당 목록: {restaurants}

        고려사항:
        1. 시간대별 적합한 메뉴 (아침: 가벼운 식사, 점심/저녁: 식사 메뉴)
        2. 이동 동선 최적화 (같은 지역 내 식당 우선)
        3. 식당 운영시간 고려
        4. 평점과 리뷰 수 반영
        5. 그룹 구성원에 적합한 메뉴

        응답 형식:
        {{
        "recommendations": [
            {{
            "restaurant_id": "실제 place_id",
            "meal_time": "아침/점심/저녁",
            "day": 숫자(1부터 시작),
            "order": 숫자(1부터 시작),
            "reason": "추천 이유(메뉴, 특징, 선택 이유 포함)"
            }}
        ]
        }}

        필수 규칙:
        1. 반드시 JSON 형식으로만 응답 (추가 설명 X)
        2. 제공된 실제 place_id만 사용
        3. {total_meals}회 만큼 추천
        4. day와 order는 반드시 숫자로 출력
        5. 각 식사 시간대에 적합한 메뉴 추천
        6. 하루 최대 3끼, 마지막 날은 2끼까지만 추천
        """)

        details_prompt = PromptTemplate.from_template("""
        당신은 한국의 모든 맛집에 대한 상세 정보를 제공하는 미식 전문 AI입니다.
        
        식당 정보:
        {restaurant_info}
        식사 시간대: {meal_time}

        다음을 포함하여 한 문단으로 설명해주세요:
        - 대표 메뉴와 특징
        - {meal_time} 추천 메뉴
        - 주변 정보
        - 방문 팁
        """)

        self.analysis_chain = analysis_prompt | self.llm
        self.recommendation_chain = recommendation_prompt | self.llm
        self.details_chain = details_prompt | self.llm

    def _calculate_meals(self, start_date: str, end_date: str) -> int:
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        days = (end - start).days + 1

        if days == 1:
            return 2 if end.hour < 18 else 3
        
        total_meals = (days - 1) * 3 + (2 if end.hour < 18 else 3)
        return total_meals

    def search_restaurants(self, location: str) -> List[Dict]:
        try:
            geocode_result = self.gmaps.geocode(location)
            if not geocode_result:
                return []

            lat = geocode_result[0]['geometry']['location']['lat']
            lng = geocode_result[0]['geometry']['location']['lng']

            places = self.gmaps.places_nearby(
                location=(lat, lng),
                radius=1500,
                keyword='맛집',
                language='ko',
                type='restaurant'
            )

            return places.get('results', [])[:15]
        except Exception as e:
            print(f"검색 오류: {e}")
            return []

    def process_recommendation(self, plan_data: Dict) -> Dict:
        try:
            keywords = self.analysis_chain.invoke({
                "location": plan_data['plan']['main_location'],
                "start_date": plan_data['plan']['start_date'],
                "end_date": plan_data['plan']['end_date'],
                "concepts": ", ".join(plan_data['plan']['concepts'])
            }).content

            restaurants = self.search_restaurants(plan_data['plan']['main_location'])
            total_meals = self._calculate_meals(
                plan_data['plan']['start_date'],
                plan_data['plan']['end_date']
            )

            response = self.recommendation_chain.invoke({
                "keywords": keywords,
                "restaurants": json.dumps(restaurants, ensure_ascii=False),
                "total_meals": total_meals
            }).content

            # ```json과 ```를 제거
            cleaned_response = response.replace("```json", "").replace("```", "").strip()
            recommendations = json.loads(cleaned_response)

            spots = []
            for rec in recommendations.get('recommendations', []):
                if validated := self.validate_restaurant(rec['restaurant_id'], rec):
                    spots.append(validated)

            return {
                "data": [
                    {"plan": plan_data['plan']},
                    {"Spots": spots}
                ]
            }
        except Exception as e:
            print(f"추천 처리 오류: {e}")
            return {"data": [{"plan": plan_data['plan']}, {"Spots": []}]}

    def validate_restaurant(self, place_id: str, meal_info: Dict) -> Optional[Dict]:
        try:
            details = self.gmaps.place(
                place_id,
                fields=['name', 'formatted_address', 'rating', 'user_ratings_total',
                        'opening_hours', 'formatted_phone_number', 'website', 'url'],
                language='ko'
            )['result']

            if details.get('rating', 0) >= 4.0:
                description = self.details_chain.invoke({
                    'restaurant_info': json.dumps(details, ensure_ascii=False),
                    'meal_time': meal_info.get('meal_time', '점심')
                }).content

                return {
                    'kor_name': details.get('name'),
                    'eng_name': details.get('name'),
                    'description': description,
                    # ... [나머지 필드들은 동일]
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
            "end_date": "2025-01-27T16:00:00"
        }
    }
    
    result = recommender.process_recommendation(plan_data)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
