import os
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOpenAI
import googlemaps
import json

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_MAP_API_KEY = os.getenv("GOOGLE_MAP_API_KEY")

llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=OPENAI_API_KEY)
gmaps = googlemaps.Client(key=GOOGLE_MAP_API_KEY)

def search_google_places(location, radius=1500):
    geocode_result = gmaps.geocode(location)
    if not geocode_result:
        return None
    
    lat = geocode_result[0]['geometry']['location']['lat']
    lng = geocode_result[0]['geometry']['location']['lng']
    
    result = gmaps.places(
        f"{location} 맛집",
        location=(lat, lng),
        radius=radius,
        language='ko'
    )
    
    restaurants = []
    for place in result['results'][:15]:
        details = gmaps.place(
            place['place_id'],
            fields=['name', 'rating', 'user_ratings_total', 'formatted_address', 
                   'price_level'],
            language='ko'
        )['result']
        
        if details.get('rating', 0) >= 4.0 and details.get('user_ratings_total', 0) >= 100:
            restaurants.append({
                'name': details.get('name'),
                'address': details.get('formatted_address'),
                'rating': details.get('rating'),
                'reviews_count': details.get('user_ratings_total'),
                'price_level': details.get('price_level')
            })
    
    restaurants.sort(key=lambda x: (x['rating'], x['reviews_count']), reverse=True)
    return restaurants

def generate_restaurant_recommendations(keywords):
   restaurants_data = search_google_places(keywords['location'])
   
   if not restaurants_data:
       return "식당 정보를 찾을 수 없습니다."

   user_data_description = f"""
   당신은 식당 추천 전문가입니다. 다음 여행 정보를 바탕으로 최적의 식당을 추천해주세요:
   - 위치: {keywords['location']}
   - 날짜: {keywords['dates']}
   - 연령대: {keywords['age_group']}
   - 그룹: 성인 {keywords['group']['adults']}, 아동 {keywords['group']['children']}, 반려동물 {keywords['group']['pets']}
   - 테마: {', '.join(keywords['themes'])}

   실제 식당 데이터:
   {json.dumps(restaurants_data, ensure_ascii=False, indent=2)}

   다음 규칙을 따라 추천해주세요:
   - 전체 여행일(1월 22일~24일)은 하루 3끼 추천
   - 마지막 여행일(1월 25일)은 2끼 추천
   - 평점과 리뷰가 많은 순으로 우선 추천
   - 아이와 반려동물 동반 가능한 곳 우선 추천

   다음 JSON 형식으로 응답해주세요:
   {{
       "recommendations": [
           {{
               "day": "1일차",
               "order": "1",
               "name": "식당명",
               "description": "설명",
               "address": "주소",
               "rating": "평점",
               "photo_url": "사진URL",
               "reason": "추천이유"
           }}
       ]
   }}
   """

   try:
       response = llm.predict(user_data_description)
       return response.strip()
   except Exception as e:
       print(f"오류 발생: {e}")
       return "추천 실패"

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