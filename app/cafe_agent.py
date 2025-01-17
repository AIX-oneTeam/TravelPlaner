from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, Tool
from langchain.agents.agent_types import AgentType
import requests
from langchain.tools import tool

import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경 변수에서 API 키 가져오기
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_SECRET_ID = os.getenv("NAVER_SECRET_ID")

@tool
def find_cafes_with_naver(location: str) -> str:
    """
    Naver 지도 API를 사용해 특정 지역과 유형의 카페를 검색합니다.
    """
    url = "https://openapi.naver.com/v1/search/local.json"
    
    params = {
        "query": f"{location} {cafe_type} 카페",
        "display": 5,  # 결과 개수 (최대 5개)
        "start": 1,    # 시작 위치
        "sort": "random"  # 결과 정렬 방식 (random: 임의 정렬)
    }
    
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_SECRET_ID
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        results = response.json().get("items", [])
        if not results:
            return "No cafés found for the given criteria."
        
        # 포맷된 결과 문자열 생성
        cafes = []
        for cafe in results:
            cafes.append(
                f"""
                한글 이름: {cafe.get("title").replace("<b>", "").replace("</b>", "")}
                설명: {cafe.get("description")}
                주소: {cafe.get("address")}
                웹 주소: {cafe.get("link")}
                지도 링크: https://map.naver.com/v5/search/{cafe.get("title")}
                전화번호: {cafe.get("telephone", "N/A")}
                """
            )
        return "\n".join(cafes)
    else:
        return f"Failed to fetch data from Naver API. Error: {response.status_code}"


# OpenAI LLM 초기화
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
# 네이버 지도 도구 추가
tools = [
    Tool(
        name="FindDCafes",
        func=lambda query: find_cafes_with_naver("인천", "디저트"),
        description="Finds dessert cafés in Incheon using Naver API."
    ),
    Tool(
        name="FindVeganCafes",
        func=lambda query: find_cafes_with_naver("인천", "비건"),
        description="Finds vegan cafés in Incheon using Naver API."
    ),
    Tool(
        name="FindPetFriendlyCafes",
        func=lambda query: find_cafes_with_naver("인천", "반려동물 동반"),
        description="Finds pet-friendly cafés in Incheon using Naver API."
    )
]

# 에이전트 초기화
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# 에이전트 실행
response = agent.run("Find 5 dessert cafés in Incheon with details.")
print(response)