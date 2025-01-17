from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, Tool
from googleapiclient.discovery import build
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

# 환경 변수에서 API 키 가져오기
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CUSTOM_SEARCH_ENGINE_ID=os.getenv("GOOGLE_CUSTOM_SEARCH_ENGINE_ID")
GOOGLE_SEARCH_API_KEY=os.getenv("GOOGLE_SEARCH_API_KEY")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_SECRET_ID = os.getenv("NAVER_SECRET_ID")

# Google Search Tool
def google_search(query: str, num_results: int = 5) -> str:
    service = build("customsearch", "v1", developerKey=GOOGLE_SEARCH_API_KEY)
    results = service.cse().list(q=query, cx=GOOGLE_CUSTOM_SEARCH_ENGINE_ID, num=num_results).execute()
    output = []
    for item in results.get("items", []):
        output.append(f"Title: {item['title']}\nLink: {item['link']}\nSnippet: {item['snippet']}\n")
    return "\n".join(output)

# Define the user request
user_request = """
지역: 인천
일정: 2박 3일
나이: 30대
일행: 성인 2명, 반려견 1명
목적: 힐링 여행
타입: 반려견 동반 가능, 디저트 카페, 로스터리 카페
"""

# Create a prompt template for generating a search query
prompt_template = PromptTemplate(
    input_variables=["request"],
    template="""
Generate a search query to find 5 cafes that match the following travel preferences:

{request}

Each cafe should have a short description, including its location, amenities, and why it's a good fit for the criteria.
"""
)

# Initialize the LLM (e.g., OpenAI's GPT model)
llm = ChatOpenAI(temperature=0, model="gpt-4")

# Create the chain to generate a search query
query_chain = LLMChain(llm=llm, prompt=prompt_template)

# Generate the search query
search_query = query_chain.run(user_request)

# Wrap the search function as a tool
tools = [
    Tool(
        name="GoogleSearch",
        func=lambda q: google_search(q),
        description="Search for cafes and their details on the web using Google."
    )
]

# Initialize an agent with the tools
agent = initialize_agent(
    tools, llm, agent="zero-shot-react-description", verbose=True
)

# Execute the search using the agent
result = agent.run(search_query)

# Display the result
print("\n--- Search Results ---\n")
print(result)


# 결과
# > Entering new AgentExecutor chain...
# The question is asking for recommendations of dessert roastery cafes in Incheon where pets are allowed. 
# Action: GoogleSearch
# Action Input: "인천 반려견 동반 가능한 디저트 로스터리 카페 추천"
# Observation: Title: [디벨로핑룸 연수점] 인천 연수구 로스터리 브루잉 카페 추천/ 연수구 ...
# Link: https://blog.naver.com/PostView.nhn?blogId=rmmma&logNo=223673199269&redirect=Dlog&widgetTypeCall=true
# Snippet: Nov 26, 2024 ... ... 디저트 카페 추천. 프로필 · 투슬와이프. 2024. 11 ... 반려견 동반이 가능해서 눈치 보지 않고. 편안하게 커피를 마실 수 있어서 좋더라고요! ​. 강아지 ...

# Title: 인천 송도 카페 추천 엘에스프레소 실내 애견동반 가능 : 네이버 블로그
# Link: https://blog.naver.com/PostView.nhn?blogId=hhh_jns&logNo=223531221009&redirect=Dlog&widgetTypeCall=true
# Snippet: Jul 31, 2024 ... 건물 주차 3시간 지원, 배달, 로스터리,. 애견동반 반려견 동반. 송도 애견동반 카페. 엘에스프레소 위치. 엘에스프레소는 건물 주차가 가능해요. (3시간).

# Title: 판교 백현카페거리 디켄트 로스터리, 유아동반 반려견동반 가능 ...
# Link: https://blog.naver.com/PostView.nhn?blogId=inopts&logNo=223485859199&redirect=Dlog&widgetTypeCall=true
# Snippet: Jun 20, 2024 ... 디저트는 발로나 초코쿠키, 쑥 티그레,. 버터바, 바나나푸딩, 디켄트 애플 치즈케이크가 있었고요. ​. ​. ​. ​. 계절 착즙주스(오렌지) - 8,000. 아이스 ...

# Title: 인천 중구 내동 카페 블루노트 커피 로스터스(bluenote coffee roasters ...
# Link: https://blog.naver.com/dazzleling/222571228517?viewType=pc
# Snippet: Nov 17, 2021 ... ... 동반이 가능한 곳이더라구요. 리드줄은 당연히 필수이고 큰 나무 화분 아래에 강아지. 물 그릇도 준비되어 있는 점이 참 섬세하다고 느꼈어요.

# Title: 한국의 발리! 애견동반 선재도 뻘다방 카페 : 네이버 블로그
# Link: https://blog.naver.com/mungderi/223406623946
# Snippet: Apr 9, 2024 ... 애견동반 가능한 카페 뻘다방. 포스팅 시작해볼께요. 뻘다방. 인천 ... 이국적인 로스터리 카페에요. ​. 세계곳곳 스페셜티커피농장과 연결되어 ...
# ...
# Here are some dessert roastery cafes in Incheon where pets are allowed:
# 1. 디벨로핑룸 연수점 located in 연수구. You can enjoy coffee without feeling uncomfortable because pets are allowed. [More Info](https://blog.naver.com/PostView.nhn?blogId=rmmma&logNo=223673199269&redirect=Dlog&widgetTypeCall=true)
# 2. 엘에스프레소 located in 송도. This cafe supports building parking for 3 hours, delivery, and roastery. Pets are also allowed. [More Info](https://blog.naver.com/PostView.nhn?blogId=hhh_jns&logNo=223531221009&redirect=Dlog&widgetTypeCall=true)
# 3. 블루노트 커피 로스터스 located in 중구. This cafe allows pets and even prepares a water bowl for dogs under a large tree pot. [More Info](https://blog.naver.com/dazzleling/222571228517?viewType=pc)
# Output is truncated. View as a scrollable element or open in a text editor. Adjust cell output settings...

########################## AI 툴로 쓰려고 했는데 네이버 API호출이 안됨
import requests

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
