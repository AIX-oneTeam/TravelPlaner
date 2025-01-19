import os
import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, Tool
from langchain.agents.agent_types import AgentType
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# .env 파일 로드
load_dotenv()

# 환경 변수 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# 프롬프트 템플릿 정의
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

# 네이버 검색 API 호출 함수
def naver_search_tool(query: str, display: int = 5, start: int = 1, sort: str = "random") -> str:
    """
    네이버 로컬 검색 API를 사용해 데이터를 검색합니다.
    """
    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {
        "query": query,
        "display": display,
        "start": start,
        "sort": sort,
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        results = response.json().get("items", [])
        if not results:
            return "검색 결과가 없습니다."

        summaries = []
        for result in results:
            title = result.get("title", "제목 없음").replace("<b>", "").replace("</b>", "")
            description = result.get("description", "설명 없음")
            address = result.get("address", "주소 없음")
            link = result.get("link", "링크 없음")
            summaries.append(f"제목: {title}\n설명: {description}\n주소: {address}\n링크: {link}\n")

        return "\n".join(summaries)
    else:
        return f"네이버 API 호출 실패: {response.status_code}, {response.text}"

# LLM 분석 함수
def analyze_naver_results(data: str, location: str) -> str:
    """
    LLM을 사용하여 네이버 검색 결과를 분석하고, 프롬프트 형식에 맞춰 결과 반환.
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=OPENAI_API_KEY)
    llm_chain = LLMChain(prompt=analysis_prompt, llm=llm)
    response = llm_chain.run({"data": data, "location": location})
    return response

# 네이버 검색 + 분석 함수
def naver_search_and_analyze(query: str, location: str, display: int = 5) -> str:
    """
    네이버 검색 API를 사용해 데이터를 가져오고, 이를 LLM으로 분석하여 결과 반환.
    """
    search_results = naver_search_tool(query=query, display=display)
    if "검색 결과가 없습니다." in search_results or "네이버 API 호출 실패" in search_results:
        return search_results

    return analyze_naver_results(search_results, location)

# Tool 정의
naver_analysis_tool = Tool(
    name="NaverSearchAnalyzer",
    func=lambda query: naver_search_and_analyze(query, "서울"),
    description="네이버 검색을 통해 서울의 관광지를 추천합니다."
)

# 에이전트 초기화
agent = initialize_agent(
    tools=[naver_analysis_tool],
    llm=ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=OPENAI_API_KEY),
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=False  # 디버깅 로그 비활성화
)

# 에이전트 실행
def run_agent_for_query(query: str) -> str:
    """
    LangChain 에이전트를 사용해 사용자 요청 처리.
    """
    response = agent.run(query)
    return response

# 테스트 실행
if __name__ == "__main__":
    user_query = "축제에 대한 컨셉으로 서울 놀러갈건데 추천해줘."
    print(f"User Query: {user_query}")
    response = run_agent_for_query(user_query)
    print("\nAgent Response:")
    print(response)
