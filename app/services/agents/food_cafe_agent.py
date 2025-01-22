# services/agents/food_cafe_agent.py

from crewai import Agent
import requests
import os

# 네이버 API 키 (환경변수 또는 직접 하드코딩 가능 - 예시는 환경변수 사용)
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "YOUR_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "YOUR_SECRET")


def create_food_cafe_agent():
    # 이 함수가 실제 네이버 API를 호출하여
    # "picture_url", "name", "description"을 갖는 딕셔너리 리스트를 반환하도록 구성
    async def search_food_cafe(query: str):
        url = "https://openapi.naver.com/v1/search/local.json"
        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
        }
        params = {"query": query, "display": 5}  # 상위 5개만
        response = requests.get(url, headers=headers, params=params)
        data = response.json()

        # items 예시: [{
        #   "title": "<b>맛집</b> ...",
        #   "link": "http://...",
        #   "category": "음식점>한식",
        #   "description": "",
        #   "telephone": "",
        #   "address": "서울특별시 ...",
        #   "roadAddress": "서울특별시 ...",
        #   "mapx": "123456",
        #   "mapy": "654321"
        # }, ...]
        results = []
        for item in data.get("items", []):
            title_clean = item["title"].replace("<b>", "").replace("</b>", "")
            category = item["category"]
            road_addr = item.get("roadAddress", "")

            results.append({
                "picture_url": "https://via.placeholder.com/150",  # 네이버 지역검색에는 이미지가 없음 (임시 URL)
                "name": title_clean,
                "description": f"{road_addr} / {category}"
            })

        return results

    # 실제 에이전트 객체 생성
    return Agent(
        role="맛집/카페 전문가",
        goal="지역 특성과 방문자 성향에 맞는 맛집과 카페 정보를 반환",
        backstory="네이버 지역검색 API를 통해 관련 정보를 가져온 뒤 picture_url, name, description을 구성",
        tools=[search_food_cafe]
    )
