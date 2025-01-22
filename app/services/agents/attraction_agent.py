# services/agents/attraction_agent.py

from crewai import Agent
import requests
import os

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "YOUR_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "YOUR_SECRET")

def create_attraction_agent():
    async def search_attraction(query: str):
        url = "https://openapi.naver.com/v1/search/local.json"
        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
        }
        params = {"query": query, "display": 5}
        response = requests.get(url, headers=headers, params=params)
        data = response.json()

        results = []
        for item in data.get("items", []):
            title_clean = item["title"].replace("<b>", "").replace("</b>", "")
            category = item["category"]
            road_addr = item.get("roadAddress", "")

            results.append({
                "picture_url": "https://via.placeholder.com/150",
                "name": title_clean,
                "description": f"{road_addr} / {category}"
            })
        return results

    return Agent(
        role="관광지 전문가",
        goal="지역의 주요 관광지 정보를 반환",
        backstory="네이버 지역검색 API 활용",
        tools=[search_attraction]
    )
