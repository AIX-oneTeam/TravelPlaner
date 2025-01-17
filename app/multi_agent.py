from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, tool
from langchain.agents.agent_types import AgentType
import requests
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()
# 환경 변수에서 API 키 가져오기
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_SECRET_ID = os.getenv("NAVER_SECRET_ID")

def search_cafe(query, display=10, start=1, sort="random"):
    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_SECRET_ID,
        "Referer": "http://localhost:8000" 
    }

    params = {
        "query": query,
        "display": display,
        "start": start,
        "sort": sort,
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        print("Error:", response.status_code, response.text)
        return None

# 사용 예시
result = search_cafe("카페")
if result:
    for item in result.get("items", []):
        print(f"카페 이름: {item['title']}, 주소: {item['address']}")


###############################################################################
# 1. Tool (멀티에이전트 각각의 역할을 함수 형태로 구현)
###############################################################################

@tool("fetch_cafe_info", return_direct=True)
def fetch_cafe_info(location: str, cafe_type: str) -> str:
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

###############################################################################
# 2. LangChain 에이전트 설정
###############################################################################

def create_cafe_agent():
    """
    LangChain의 AgentExecutor를 생성하여,
    정의된 Tool들을 등록한 뒤 ZeroShotAgent로 동작시킵니다.
    """
    # 사용할 LLM 설정 
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)

    # 등록할 Tool 목록
    tools = [
        fetch_cafe_info
    ]

    # Agent 초기화
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,  # ZeroShotAgent 사용
        verbose=True
    )
    return agent

agent = create_cafe_agent()

user_request = """\
# 지역 : 인천
# 일정 : 2박 3일
# 나이 : 30대
# 일행 : 성인2명 반려견 1명
# 목적 : 힐링 여행
# 타입 : 반려견 동반 가능, 디저트 카페, 로스터리 카페 
"""

response = agent.run(user_request)
print(response)


