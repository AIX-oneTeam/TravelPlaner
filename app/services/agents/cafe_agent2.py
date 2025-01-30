from crewai import Agent, Crew, Process, Task, LLM
from crewai.utils import MultiAgentSystem
from openai import ChatCompletion
from typing import List, Dict

import os
from dotenv import load_dotenv
# 환경 변수 로드
load_dotenv()
# OpenAI API 키 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# LLM 초기화
my_llm = LLM(
    model="gpt-4o-mini",
    api_key=OPENAI_API_KEY,
    temperature=0,
    # max_tokens=4000
)

class LLMBaseAgent(Agent):
    def __init__(self):
        self.llm = ChatCompletion(api_key=OPENAI_API_KEY)

    def query_llm(self, prompt: str) -> str:
        """LLM에 쿼리하여 응답을 반환."""
        response = self.llm.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response['choices'][0]['message']['content']

# 에이전트 정의
search_agent = Agent(
    role='검색 전문가',
    goal='사용자의 상황에 맞는 카페 조사',
    backstory="여행온 사용자에게 특별한 추억 제공",
    llm=my_llm
)

review_agent = Agent(
    role='카페 비평가',
    goal='카페별로 리뷰에서 사람들이 공통적으로 좋아하고 칭찬하는 특징 3개 추출',
    backstory="search_agent가 반환한 카페의 최신 리뷰를 조사",
    llm=my_llm
)

menu_agent = Agent(
    role='메뉴 추천 전문가',
    goal='사람들이 공통적으로 찾는 시그니처 메뉴 3가지 추출',
    backstory="search_agent가 반환한 카페의 최신 리뷰를 조사",
    llm=my_llm
)

atmosphere_agent = Agent(
    role='분위기 전문가',
    goal='사람들이 공통적으로 촬영한 사진의 특징을 3가지 추출',
    backstory="search_agent가 반환한 카페의 사진 리뷰를 조사",
    llm=my_llm
)

summarize_agent = Agent(
    role='정리 전문가',
    goal='사람들이 공통적으로 촬영한 사진의 특징을 3가지 추출',
    backstory="search_agent, review_agent, menu_agent, atmosphere_agent가 반환한 값을 정리 ",
    llm=my_llm
)

selector_agent = Agent(
    role='선택 전문가',
    goal='사용자의 상황에 맞는 카페 TOP 3제시',
    backstory="summarize_agent가 정리한 값을 바탕으로 최적의 카페 선택",
    llm=my_llm
)

qa_agent = Agent(
    role='품질 전문가',
    goal='정확한 정보 조사 및 제공',
    backstory="selector_agent가 알려준 카페가 폐업했는지 확인, 폐업했다면 운영중인 다음 순위의 카페로 대체" ,
    llm=my_llm
)

information_agent = Agent(
    role='정보 전문가',
    goal='카페의 정확한 정보 조사 및 제공',
    backstory="qa_agent와 selector_agent가 협업해 최종 결정된 3개 카페의 이름, 영문이름, 주소, 운영시간, 지도url, 대표 이미지 url, 주차가능여부, 반려견동반여부, 폐업여부 정보 추출",
    llm=my_llm
)


# 멀티 에이전트 시스템 설정
agents = {
    "search_cafe": SearchCafeAgent(),
    "review": ReviewAgent(),
    "extract_features": ExtractFeaturesAgent(),
    "recommend_menu": RecommendMenuAgent(),
    "photo": PhotoAgent(),
    "extract_photo_keywords": ExtractPhotoKeywordsAgent(),
    "summarize": SummarizeAgent(),
    "select_top_cafes": SelectTopCafesAgent(),
    "extract_cafe_details": ExtractCafeDetailsAgent()
}

multi_agent_system = MultiAgentSystem(agents)

# 실행
region = "Seoul"
traveler_context = "quiet place for work"

# Step-by-step 호출
cafes = multi_agent_system.run("search_cafe", region=region, traveler_context=traveler_context)
reviews = multi_agent_system.run("review", cafes=cafes)
features = multi_agent_system.run("extract_features", reviews=reviews)
menu = multi_agent_system.run("recommend_menu", reviews=reviews)
photos = multi_agent_system.run("photo", cafes=cafes)
photo_keywords = multi_agent_system.run("extract_photo_keywords", photos=photos)
summary = multi_agent_system.run("summarize", inputs={
    "popular_features": features["popular_features"],
    "recommended_menu": menu,
    "photo_keywords": photo_keywords,
    "cafes": cafes
})
top_cafes = multi_agent_system.run("select_top_cafes", cafes=cafes, traveler_context=traveler_context)
cafe_details = multi_agent_system.run("extract_cafe_details", top_cafes=top_cafes)

# 결과 출력
print("Summary:\n", summary)
print("Top Cafes Details:\n", cafe_details)
