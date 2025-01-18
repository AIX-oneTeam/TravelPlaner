import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, Tool
from langchain.agents.agent_types import AgentType
from langchain.prompts import PromptTemplate
from serpapi import GoogleSearch

# .env 파일 로드
load_dotenv()

# 환경 변수 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

# 프롬프트 템플릿 정의 (한국어 출력)
analysis_prompt = PromptTemplate(
    input_variables=["data", "location"],
    template="""
당신은 여행 전문가입니다. 다음 데이터를 바탕으로 {location}의 추천 관광지 목록을 작성하세요.
각 관광지에 대해 다음 정보를 포함하세요:
1. 장소 이름
2. 간단한 설명
3. 클릭 가능한 링크
4. 추가 정보 (주소, 이미지 링크 등)

분석할 데이터:
{data}

다음 형식으로 응답하세요:

다음은 {location}의 추천 관광지 목록입니다:

1. **[PLACE NAME]**
   - 설명: [SHORT DESCRIPTION]
   - 링크: [LINK]
   - 추가 정보: [ANY EXTRA INFO, LIKE IMAGE OR ADDRESS]
"""
)

# Google Search Tool
def google_search_tool(query: str, num_results: int = 3) -> str:
    """
    Google Search API를 사용해 검색 결과를 가져옵니다.
    :param query: 검색할 키워드
    :param num_results: 가져올 검색 결과 개수
    :return: 검색 결과 요약 문자열
    """
    search = GoogleSearch({
        "q": query,
        "num": num_results,
        "api_key": SERPAPI_API_KEY,
    })
    results = search.get_dict().get("organic_results", [])
    if not results:
        return "검색 결과가 없습니다."

    summaries = []
    for result in results:
        title = result.get("title", "제목 없음")
        link = result.get("link", "링크 없음")
        snippet = result.get("snippet", "설명 없음")
        summaries.append(f"제목: {title}\n설명: {snippet}\n링크: {link}\n")
    
    return "\n".join(summaries)

# LLM 분석 함수
def analyze_google_results(data: str, location: str) -> str:
    """
    LLM을 사용하여 Google 검색 결과를 분석하고, 프롬프트 형식에 맞춰 결과 반환.
    """
    llm = ChatOpenAI(model="gpt-4-mini", temperature=0, openai_api_key=OPENAI_API_KEY)
    formatted_prompt = analysis_prompt.format(data=data, location=location)
    response = llm.run(formatted_prompt)
    return response

# Google Search + 분석 함수
def google_search_and_analyze(query: str, location: str, num_results: int = 3) -> str:
    """
    Google Search API를 사용해 데이터를 가져오고, 이를 LLM으로 분석하여 결과 반환.
    """
    # Google Search 실행
    search = GoogleSearch({
        "q": query,
        "num": num_results,
        "api_key": SERPAPI_API_KEY,
    })
    results = search.get_dict().get("organic_results", [])
    if not results:
        return "검색 결과가 없습니다."

    # 검색 결과 요약
    summaries = []
    for result in results:
        title = result.get("title", "제목 없음")
        link = result.get("link", "링크 없음")
        snippet = result.get("snippet", "설명 없음")
        summaries.append(f"제목: {title}\n설명: {snippet}\n링크: {link}\n")

    # 데이터 분석 및 포맷팅
    raw_data = "\n".join(summaries)
    return analyze_google_results(raw_data, location)

# Tool 정의
google_analysis_tool = Tool(
    name="GoogleSearchAnalyzer",
    func=lambda query: google_search_and_analyze(query, "서울"),
    description="Google 검색을 통해 서울의 관광지를 추천합니다."
)

# 에이전트 초기화
agent = initialize_agent(
    tools=[google_analysis_tool],
    llm=ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=OPENAI_API_KEY),
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# 에이전트 실행
def run_agent_for_query(query: str):
    """
    LangChain 에이전트를 사용해 사용자 요청 처리.
    :param query: 사용자 입력
    :return: 에이전트 응답
    """
    response = agent.run(query)
    return response

# 테스트 실행
if __name__ == "__main__":
    user_query = "서울의 관광지를 추천해주세요."
    print(f"User Query: {user_query}")
    response = run_agent_for_query(user_query)
    print("\nAgent Response:")
    print(response)
