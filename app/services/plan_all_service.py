import traceback
import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List

# crewai - 가상의 라이브러리 예시
from crewai import Agent, Task, Crew, LLM
from crewai.tools import BaseTool


# ======================
# 🔹 환경 변수 로드
# ======================
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# ======================
# 🔹 LLM 설정
# ======================
llm = LLM(
    model="gpt-4o-mini",  # 예시용 모델명
    temperature=0,
    api_key=OPENAI_API_KEY
)

# ======================
# 🔹 Pydantic Models
# ======================
class Spot(BaseModel):
    kor_name: str
    eng_name: str
    description: str
    address: str
    zip: str
    url: str
    image_url: str
    map_url: str
    likes: int
    satisfaction: float
    spot_category: int  # 0=관광지, 1=맛집, 2=카페, 3=숙소
    phone_number: str
    business_status: bool
    business_hours: str
    order: int  # 일자별 방문 순서 (1, 2, 3...)
    day_x: int  # N일차
    spot_time: str  # ISO8601(대략적 시간)

class OutputSpots(BaseModel):
    spots: List[Spot]


# ======================
# 🔹 Tools
# ======================
class NaverWebSearchTool(BaseTool):
    """네이버 웹 검색 API를 사용해 텍스트 정보를 검색"""
    name: str = "NaverWebSearch"
    description: str = "네이버 웹 검색 API를 사용해 텍스트 정보를 검색"

    def _run(self, query: str) -> str:
        if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
            return "[NaverWebSearchTool] 네이버 API 자격 증명이 없습니다."

        url = "https://openapi.naver.com/v1/search/webkr.json"
        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
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
    """네이버 이미지 검색 API를 사용하여 장소 이미지를 가져옴"""
    name: str = "NaverImageSearch"
    description: str = "네이버 이미지 검색 API를 사용하여 장소 이미지를 가져옴"

    def _run(self, query: str) -> str:
        if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
            return "[NaverImageSearchTool] 네이버 API 자격 증명이 없습니다."

        url = "https://openapi.naver.com/v1/search/image"
        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
        }
        params = {"query": query, "display": 1, "sort": "sim"}

        try:
            resp = requests.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])

            if not items:
                return ""

            return items[0].get("link", "")  # 첫 번째 이미지 URL 반환

        except Exception as e:
            return f"[NaverImageSearchTool] 에러: {str(e)}"


# ======================
# 🔹 Helper Function
# ======================
def calculate_trip_days(start_date_str, end_date_str):
    fmt = "%Y-%m-%d"
    from datetime import datetime
    start_dt = datetime.strptime(start_date_str, fmt)
    end_dt = datetime.strptime(end_date_str, fmt)
    return (end_dt - start_dt).days + 1


# ======================
# 🔹 Agents (Backstory를 더욱 자세히)
# ======================
site_agent = Agent(
    role="관광지 평가관",
    goal="사용자 주변의 주요 관광지 정보를 심층 조사하고, 정확한 정보를 전달한다.",
    backstory="""
[관광지 평가관 백스토리]
나는 20년 경력의 국내 여행 작가이자, 
전국의 관광명소를 소개하는 잡지 <한국의 아름다움>의 편집장을 역임했다.
방대한 여행 데이터베이스와 현장 경험을 바탕으로 
인기 관광지부터 숨은 명소까지 꿰고 있다.
사용자에게 정확하고 풍부한 관광지 정보를 제공하는 것이 나의 주요 임무다.
""",
    tools=[NaverWebSearchTool()],
    llm=llm,
    verbose=True
)

cafe_agent = Agent(
    role="맛집/카페 평가관",
    goal="사용자 주변의 맛집과 카페를 조사하고, 신뢰도 높은 정보를 제공한다.",
    backstory="""
[맛집/카페 평가관 백스토리]
나는 15년 이상 전국 식당과 카페를 탐방하며, 
푸드 칼럼니스트와 레스토랑 컨설턴트로 활동해 왔다.
일식, 중식, 한식, 양식 등 다양한 분야에 전문성이 있으며, 
카페 트렌드(디저트, 스페셜티 커피 등)도 놓치지 않는다.
맛·가격·분위기·평판을 다각도로 평가해 
사용자 취향에 맞는 맛집/카페 정보를 제공한다.
""",
    tools=[NaverWebSearchTool()],
    llm=llm,
    verbose=True
)

accommodation_agent = Agent(
    role="숙소 평가관",
    goal="숙박 시설의 편의성과 만족도를 분석하고, 사용자에게 맞는 숙소를 추천한다.",
    backstory="""
[숙소 평가관 백스토리]
나는 호텔경영학 전공 후, 국내외 유명 호텔 체인에서 10년 이상 근무했다.
또한 50여 개 이상의 국내 숙박시설(호텔, 펜션, 리조트 등)을 직접 체험하고 
리뷰한 경험이 있다.
가족 여행, 커플 여행, 비즈니스 출장 등 
상황별 최적의 숙소를 찾는 데 능숙하다.
""",
    tools=[NaverWebSearchTool()],
    llm=llm,
    verbose=True
)

planning_agent = Agent(
    role="여행 일정 플래너",
    goal="모든 정보를 종합하여, 각 일자별로 시간대가 나뉜 상세 일정을 생성한다.",
    backstory="""
[여행 일정 플래너 백스토리]
나는 데이터 기반 AI 여행 플래너로, 
사용자의 여행 기간과 선호도를 분석해 효율적인 일정을 제안한다.
출발부터 귀환까지 동선, 시간, 흥미 요소를 고려해 
사용자가 편리하면서도 즐거운 여행을 할 수 있게 돕는 것이 나의 역할이다.
""",
    tools=[NaverWebSearchTool()],
    llm=llm,
    verbose=True
)

image_agent = Agent(
    role="이미지 검색 전문가",
    goal="각 장소의 대표 이미지를 찾아 여행 정보를 시각적으로 풍부하게 만든다.",
    backstory="""
[이미지 검색 전문가 백스토리]
나는 온라인 이미지 검색 기술에 정통하며, 
관광/숙박/맛집 관련 이미지를 빠르게 찾아낼 수 있다.
짧은 시간 내에 장소 이름과 연관된 이미지를 분석하여, 
가장 적절한 대표 이미지를 선택하는 것이 나의 주된 임무다.
""",
    tools=[NaverImageSearchTool()],
    llm=llm,
    verbose=True
)

address_verification_agent = Agent(
    role="주소 검증자",
    goal="최종 일정 속 각 장소의 주소가 실제 검색과 일치하는지 확인하고, 가능한 한 수정한다.",
    backstory="""
[주소 검증자 백스토리]
나는 주소·위치 데이터를 전문적으로 검수하는 QA 담당자다.
여행 관련 정보를 온라인에서 모아보면 주소가 종종 틀리거나, 
이름과 주소가 불일치하는 경우가 많다.
네이버 검색 도구를 활용해, 
최종적으로 생성된 일정의 각 장소 주소를 다시 검수하고, 
오류가 있다면 최대한 수정하는 것이 나의 임무다.
""",
    tools=[NaverWebSearchTool()],
    llm=llm,
    verbose=True
)

# ======================
# 🔹 Tasks
# ======================
def create_plan(user_input):
    """
    1) 관광지 조사
    2) 맛집/카페 조사
    3) 숙소 조사
    4) 전체 일정 생성 (모든 일자, 시간대별 9개 코스)
    5) 이미지 삽입
    6) 주소 검증 (최종)
    반환 형태:
      {
        "plan": {...},
        "spots": [...]
      }
    """
    try:
        location = user_input["location"]
        trip_days = calculate_trip_days(user_input["start_date"], user_input["end_date"])

        # -- 태스크 1: 관광지 조사
        site_task = Task(
            description=f"""
            [관광지 정보 조사]
            - '{location}' 인근 관광지 최소 10곳 이상 조사.
            - NaverWebSearchTool을 사용하여 실제 주소를 확보. 
              (장소명 + '주소' 로 검색)
            - 주소, 전화번호, 운영시간, 특징, 추천 이유 등 포함.
            - 반려동물 동반 여부 등 추가 정보도 가능하다면 포함.
            """,
            agent=site_agent,
            expected_output="관광지 목록 (텍스트)"
        )

        # -- 태스크 2: 맛집/카페 조사
        cafe_task = Task(
            description=f"""
            [맛집 및 카페 조사]
            - '{location}' 인근 맛집 10곳 이상, 카페 6곳 이상 조사.
            - 주소, 영업시간, 전화번호, 대표 메뉴, 예약 가능 여부, 
              반려동물 동반 여부 등 포함.
            - 주소는 반드시 NaverWebSearchTool을 이용해 검증.
            """,
            agent=cafe_agent,
            context=[site_task],
            expected_output="맛집 및 카페 목록 (텍스트)"
        )

        # -- 태스크 3: 숙소 조사
        accommodation_task = Task(
            description=f"""
            [숙소 조사]
            - '{location}' 인근 숙소 5곳 이상 조사.
            - 주소, 객실 정보, 주요 시설, 체크인/체크아웃 시간, 
              반려동물 가능 여부, 주차 가능 여부, 전화번호 등 포함.
            - 주소는 NaverWebSearchTool 결과 활용.
            """,
            agent=accommodation_agent,
            context=[site_task, cafe_task],
            expected_output="숙소 목록 (텍스트)"
        )

        # -- 태스크 4: 일정 생성
        planning_task = Task(
            description=f"""
            [최종 여행 일정 생성]
            - 여행 기간: {user_input['start_date']} ~ {user_input['end_date']} 
              (총 {trip_days}일)
            - **절대로 1일차만 생성하고 끝내지 말 것.** 
              Day 1부터 Day {trip_days}까지 전부 만들 것.
            - 하루 일정은 9개 방문지 (시간대 명시):
              1) 아침 맛집 (spot_category=1) - 08:00
              2) 관광지 (spot_category=0) - 10:00
              3) 카페 (spot_category=2) - 11:30
              4) 관광지 (spot_category=0) - 13:00
              5) 점심 맛집 (spot_category=1) - 14:00
              6) 관광지 (spot_category=0) - 16:00
              7) 카페 (spot_category=2) - 17:30
              8) 저녁 맛집 (spot_category=1) - 19:00
              9) 숙소 (spot_category=3) - 21:00
            - spot_time 필드를 위 시간대로 설정. 
            - **Spot 구조**:
                {{
                  "kor_name": "...",
                  "eng_name": "...",
                  "description": "...",
                  "address": "...",
                  "zip": "",
                  "url": "",
                  "image_url": "",
                  "map_url": "",
                  "likes": 0,
                  "satisfaction": 0.0,
                  "spot_category": (0~3),
                  "phone_number": "",
                  "business_status": true,
                  "business_hours": "",
                  "order": (1~9),
                  "day_x": (1~{trip_days}),
                  "spot_time": "2025-01-01T08:00:00+09:00"
                }}
            - **맛집(1)은 음식점 정보**만, 카페(2)는 디저트/커피 위주,
              관광지(0)는 공원·유적·전시 등,
              숙소(3)는 호텔/펜션/게스트하우스 등. 
              카테고리와 설명 충돌 없도록 주의!
            - Day 1부터 Day {trip_days}까지 
              (order=1~9) * {trip_days}개의 Spot을 JSON 배열 "spots"에 담아 출력.
            - 출력 전, 카테고리와 설명이 어긋나지 않는지 스스로 확인.
            - JSON 외에 다른 설명은 최소화.
            """,
            agent=planning_agent,
            context=[site_task, cafe_task, accommodation_task],
            expected_output="spots 리스트를 담은 JSON 텍스트 (day_x=1..N, order=1..9)"
        )

        # -- 태스크 5: 이미지 삽입
        image_task = Task(
            description=f"""
            [이미지 삽입]
            - 상기 일정 JSON(spot 리스트)에서 kor_name으로 이미지 검색(NaverImageSearch).
            - 검색 결과 중 첫 번째 이미지를 image_url에 입력.
            - 최종 JSON은 {{
                "spots": [ ... ]
              }} 형태로 출력.
            """,
            agent=image_agent,
            context=[planning_task],
            expected_output="이미지가 추가된 최종 JSON (spots)",
            output_json=OutputSpots
        )

        # -- 태스크 6: 주소 검증
        verification_task = Task(
            description=f"""
            [주소 검증]
            - 상기의 최종 일정 JSON에서, 각 spot의 "address" 필드를 다시 점검.
            - NaverWebSearchTool로 "address"를 검색해서 실제 존재 여부를 대략적으로 확인.
            - 만약 주소가 검색 결과와 전혀 안 맞거나, 
              맛집(1)인데 '해산물 맛집'이라고 하면서 카페로 나오는 등 
              카테고리가 뒤섞인 경우가 있으면, 
              가능하다면 주소나 설명을 수정해서 재출력.
            - 최종 JSON:
              {{
                "spots": [ ... ]
              }}
            - (주의) 100% 완벽한 검증은 어려울 수 있으니, 
              최대한 검색 결과와 일치하는 주소를 반영하도록 노력.
            """,
            agent=address_verification_agent,
            context=[image_task],  # 이미지 삽입 후 최종 검증
            expected_output="주소 검수까지 완료된 최종 JSON (spots)",
            output_json=OutputSpots
        )

        # ==================
        # 3️⃣ Crew 실행
        # ==================
        crew = Crew(
            agents=[
                site_agent,
                cafe_agent,
                accommodation_agent,
                planning_agent,
                image_agent,
                address_verification_agent
            ],
            tasks=[
                site_task,
                cafe_task,
                accommodation_task,
                planning_task,
                image_task,
                verification_task
            ],
            verbose=True
        )

        final_result = crew.kickoff()  # pydantic(OutputSpots)

        # pydantic -> dict 변환
        final_dict = final_result.dict()
        spots = final_dict.get("spots", [])

        # ==================
        # 4️⃣ JSON 형태로 반환
        # ==================
        return {
            "plan": {
                "name": user_input.get("name", "여행 일정"),
                "start_date": user_input["start_date"],
                "end_date": user_input["end_date"],
                "main_location": location,
                "ages": user_input.get("ages", 0),
                "companion_count": sum(user_input.get("companions", {}).values()),
                "concepts": ", ".join(user_input.get("concepts", [])),
                "member_id": user_input.get("member_id", 0),
                "created_at": datetime.now().strftime("%Y-%m-%d"),
                "updated_at": datetime.now().strftime("%Y-%m-%d")
            },
            "spots": spots
        }

    except Exception as e:
        print(f"[ERROR] {e}")
        traceback.print_exc()
        return {"error": str(e)}
