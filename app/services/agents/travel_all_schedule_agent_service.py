import json
import traceback
import os
import requests
from crewai import Agent, Task, Crew, LLM
from datetime import datetime, time
from dotenv import load_dotenv
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class spot_pydantic(BaseModel):

    kor_name: str = Field(max_length=255)
    eng_name: str = Field(default=None, max_length=255)
    description: str = Field(max_length=255)
    address: str = Field(max_length=255)
    url: str = Field(default=None, max_length=2083)
    image_url: str = Field(max_length=2083)
    map_url: str = Field(max_length=2083)
    latitude: float
    longitude: float
    spot_category: int
    phone_number: str = Field(default=None, max_length=300)
    business_status: bool = None
    business_hours: str = Field(default=None, max_length=255)

    order: int
    day_x: int
    spot_time: str = None
    
class spots_pydantic(BaseModel):
    spots: list[spot_pydantic]


# 🔹 환경 변수 로드
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AGENT_NAVER_CLIENT_ID = os.getenv("AGENT_NAVER_CLIENT_ID")
AGENT_NAVER_CLIENT_SECRET = os.getenv("AGENT_NAVER_CLIENT_SECRET")

# 🔹 LLM 설정 (객체 호출 X)
llm = LLM(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY)
class NaverWebSearchTool(BaseTool):
    """네이버 웹 검색 API를 사용해 텍스트 정보를 검색"""
    name: str = "NaverWebSearch"
    description: str = "네이버 웹 검색 API를 사용해 텍스트 정보를 검색"

    def _run(self, query: str) -> str:
        if not AGENT_NAVER_CLIENT_ID or not AGENT_NAVER_CLIENT_SECRET:
            return "[NaverWebSearchTool] 네이버 API 자격 증명이 없습니다."

        url = "https://openapi.naver.com/v1/search/webkr.json"
        headers = {
            "X-Naver-Client-Id": AGENT_NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": AGENT_NAVER_CLIENT_SECRET,
        }
        params = {"query": query, "display": 3, "start": 1, "sort": "random"}

        try:
            resp = requests.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])

            if not items:
                return f"[NaverWebSearchTool] '{query}' 검색 결과 없음."

            results = []
            for item in items:
                title = item.get("title", "")
                link = item.get("link", "")
                desc = item.get("description", "")
                results.append(f"제목: {title}\n링크: {link}\n설명: {desc}\n")

            return "\n".join(results)

        except Exception as e:
            return f"[NaverWebSearchTool] 에러: {str(e)}"


class NaverImageSearchTool(BaseTool):
    """네이버 이미지 검색 API를 사용하여 이미지 URL을 가져옴"""

    name: str = "NaverImageSearch"
    description: str = "네이버 이미지 검색 API를 사용하여 장소 관련 이미지를 가져옴"

    def _run(self, query: str) -> str:
        if not AGENT_NAVER_CLIENT_ID or not AGENT_NAVER_CLIENT_SECRET:
            return "[NaverImageSearchTool] 네이버 API 자격 증명이 없습니다."

        url = "https://openapi.naver.com/v1/search/image"
        headers = {
            "X-Naver-Client-Id": AGENT_NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": AGENT_NAVER_CLIENT_SECRET,
        }
        params = {"query": query, "display": 1, "sort": "sim"}

        try:
            resp = requests.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])

            if not items:
                return ""

            return items[0].get("link", "")  # ✅ 첫 번째 이미지 URL 반환

        except Exception as e:
            return f"[NaverImageSearchTool] 에러: {str(e)}"


# 🔹 날짜 계산 함수
def calculate_trip_days(start_date_str, end_date_str):
    fmt = "%Y-%m-%d"
    start_dt = datetime.strptime(start_date_str, fmt)
    end_dt = datetime.strptime(end_date_str, fmt)
    delta = end_dt - start_dt
    return delta.days + 1


def create_plan(user_input):
    """
    CrewAI를 실행하여 여행 일정을 생성하는 서비스.
    - CrewAI 자체 비동기 기능을 활용하므로 FastAPI `async` 처리 불필요.
    - 반환 값은 JSON 형식 (plan + spots 리스트 포함)
    """
    try:
        # location = user_input["location"]
        main_location = user_input.get("main_location", "Unknown Location")
        trip_days = calculate_trip_days(
            user_input["start_date"], user_input["end_date"]
        )

        # 1️⃣ 에이전트 생성
        site_agent = Agent(
            role="관광지 평가관",
            goal="사용자 주변 관광지 정보를 제공",
            backstory="""
            나는 대한민국에서 손꼽히는 여행 전문가이며, 특히 관광지에 대한 데이터베이스를 방대하게 보유하고 있다.  
            20년 이상 여행 가이드 및 여행 컨설팅을 진행하며, 전국의 숨은 명소와 필수 방문지를 완벽하게 파악하고 있다.  
            최신 트렌드를 반영한 관광지 추천과 맞춤형 여행지를 제공하는 것이 나의 강점이다.
            """,
            tools=[NaverWebSearchTool()],
            llm=llm,
            verbose=True,
        )

        cafe_agent = Agent(
            role="맛집/카페 평가관",
            goal="사용자 주변의 최고 맛집과 카페 정보를 제공",
            backstory="""
            나는 미슐랭 가이드 수준의 미식가이며, 대한민국 전역의 맛집과 카페를 연구해왔다.  
            20년 동안 푸드 칼럼니스트와 레스토랑 컨설턴트로 활동하며, 수천 개의 맛집과 카페를 직접 경험하고 평가했다.  
            각 지역의 대표 맛집뿐만 아니라 숨겨진 로컬 핫플도 정확히 추천할 수 있다.
            """,
            tools=[NaverWebSearchTool()],
            llm=llm,
            verbose=True,
        )

        accommodation_agent = Agent(
            role="숙소 평가관",
            goal="사용자에게 최적의 숙소를 추천",
            backstory="""
            나는 국내외 호텔 및 숙소 리뷰 전문가로, 호텔 경영학을 전공하고 글로벌 호텔 체인에서 근무한 경험이 있다.  
            20년 동안 호텔 및 숙박 시설을 직접 체험하며, 고객 만족도와 시설 평가에 대한 높은 전문성을 갖추고 있다.  
            여행자의 니즈에 맞는 최적의 숙소를 찾아주는 것이 나의 특기이다.
            """,
            tools=[NaverWebSearchTool()],
            llm=llm,
            verbose=True,
        )

        planning_agent = Agent(
            role="여행 일정 플래너",
            goal="사용자의 여행 스타일에 맞춘 최적의 일정을 생성",
            backstory="""
            나는 AI 기반 여행 플래너로, 20년 이상 개인 맞춤형 여행 일정을 기획해왔다.  
            데이터 분석과 최신 트렌드를 기반으로 사용자의 취향을 반영한 여행 계획을 세우는 것이 나의 강점이다.  
            여행 동선 최적화, 시간 배분, 피로도 조절까지 고려하여 완벽한 일정을 구성할 수 있다.
            """,
            tools=[NaverWebSearchTool()],
            llm=llm,
            verbose=True,
        )
        image_agent = Agent(
            role="이미지 검색 전문가",
            goal="각 장소에 대한 관련 이미지를 찾아 제공",
            backstory="""
            나는 수년간 여행과 관광지의 시각적 자료를 연구한 전문가이다.
            최신 AI 기반 이미지 검색 기술을 활용하여 장소에 대한 고품질 이미지를 찾고 제공할 수 있다.
            """,
            tools=[NaverImageSearchTool()],
            llm=llm,
            verbose=True,
        )

        # 2️⃣ 태스크 생성
        site_task = Task(
            description=f"""
            [관광지 정보 조사]
            - '{main_location}' 인근 관광지 최소 5곳 조사.
            - 주소, 운영시간, 입장료, 특징, 추천 이유, 반려동물 동반 가능 여부 포함.
            """,
            agent=site_agent,
            expected_output="관광지 목록 (텍스트)",
            # async_execution=True,
        )

        cafe_task = Task(
            description=f"""
            [맛집 및 카페 조사]
            - '{main_location}' 인근 맛집 5곳 이상, 카페 3곳 이상 조사.
            - 주소, 영업시간, 대표 메뉴, 예약 가능 여부, 반려동물 동반 가능 여부 포함.
            """,
            agent=cafe_agent,
            context=[site_task],
            expected_output="맛집 및 카페 목록 (텍스트)",
            # async_execution=True,
        )

        accommodation_task = Task(
            description=f"""
            [숙소 조사]
            - '{main_location}' 인근 숙소 5곳 이상 조사.
            - 주소, 객실 정보, 주요 시설, 체크인/체크아웃 시간, 반려동물 가능 여부, 주차 가능 여부 포함.
            """,
            agent=accommodation_agent,
            context=[site_task, cafe_task],
            expected_output="숙소 목록 (텍스트)",
            # async_execution=True,
        )

        planning_task = Task(
            description=f"""
            [최종 여행 일정 생성]
            - 여행 기간: {user_input['start_date']} ~ {user_input['end_date']} (총 {trip_days}일)
            - 매일 포함될 요소:
                - 맛집 3곳 (아침, 점심, 저녁)
                - 카페 2곳
                - 관광지 3곳
                - 숙소 1곳
            - 모든 장소는 기간 구분 없이 모두 spots 이라는 단일 리스트에 포함.
            - 각 장소는 spot이라는 이름을 가지며, 필드는 다음과 같음:
            {{
                "kor_name": "string",
                "eng_name": "string",
                "description": "string",
                "address": "string",
                "zip": "string",
                "url": "string",
                "image_url": "string",
                "map_url": "string",
                "likes": 0,
                "satisfaction": 0,
                "spot_category": 0,
                "phone_number": "string",
                "business_status":True,
                "business_hours": "string",
                "order": 0,
                "day_x": 0,
                "spot_time": "2025-06-01T06:27:43.593Z"
            }}
            - 각 장소는 day_x, order 필드로 일정에 포함될 날짜와 순서를 지정.
            - day_x는 반드시 1부터 시작하여 증가하는 숫자이며, 여행 기간의 각각의 날짜를 의미함.
            - order는 반드시 0부터 시작하여 증가하는 숫자이며, 각 날짜 내에서 장소의 순서를 의미함.
            - 각 장소는 spot_category 필드로 관광지, 맛집, 카페, 숙소를 구분, 0은 숙소, 1은 관광지, 2는 카페, 3은 맛집임. 
            - spot_time 형식은 '%H:%M:%S' 형식의 문자열로 변환
            """,
            agent=planning_agent,
            context=[
                site_task,
                cafe_task,
                accommodation_task,
            ],  # ✅ 기존 태스크(관광지, 숙소, 맛집) 결과를 활용
            expected_output="pydantic 형식의 여행 일정 데이터",  
            output_pydantic=spots_pydantic,  
        )

        image_task = Task(
            description=f"""
            [이미지 삽입]
            - CrewAI가 생성한 여행 일정 pydantic 형식에서 각 장소의 `kor_name`을 기반으로 이미지를 검색.
            - 검색된 이미지를 `image_url` 필드에 추가.
            - 각 필드를 spot_request 형식으로 변환.
            - 모든 장소는 기간 구분 없이 spots라는 단일 리스트에 포함.
            """,
            agent=image_agent,
            context=[planning_task],  # ✅ 여행 일정 생성 이후 실행
            expected_output="pydantic 형식의 여행 일정 데이터",
            output_pydantic=spots_pydantic,
        )

        # 3️⃣ Crew 실행 (🚨 `await` 사용 금지)
        crew = Crew(
            agents=[
                site_agent,
                cafe_agent,
                accommodation_agent,
                planning_agent,
                image_agent,
            ],
            tasks=[site_task, cafe_task, accommodation_task, planning_task, image_task],
            verbose=True,
        )

        final_result = crew.kickoff()
        print("final_result", final_result)
        print("image_task.output", image_task.output)


        # 4️⃣ Crew 결과를 dict 형식으로 변환
        response_json = {
            "message": "요청이 성공적으로 처리되었습니다.",
            "plan": {
                "name": user_input.get("name", "여행 일정"),
                "start_date": user_input["start_date"],
                "end_date": user_input["end_date"],
                "main_location": main_location,
                "ages": user_input.get("ages", 0),
                "companion_count": sum(
                    companion.get("count", 0)
                    for companion in user_input.get("companions", [])
                ),
                "concepts": ", ".join(user_input.get("concepts", [])),
                "member_id": user_input.get("member_id", 0),
                "created_at": datetime.now().strftime("%Y-%m-%d"),
                "updated_at": datetime.now().strftime("%Y-%m-%d"),
            },
            "spots": image_task.output.pydantic.model_dump()
        }



        return response_json

    except Exception as e:
        print(f"[ERROR] {e}")
        traceback.print_exc()
        return {"message": "요청 처리 중 오류가 발생했습니다.", "error": str(e)}
