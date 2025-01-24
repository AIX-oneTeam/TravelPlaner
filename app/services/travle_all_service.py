from dotenv import load_dotenv
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun
import os
from crewai.tools import BaseTool
from typing import Optional

# .env 파일 로드
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print(f"API KEY 확인: {'있음' if OPENAI_API_KEY else '없음'}")

# LLM 초기화
gpt = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=OPENAI_API_KEY,
    temperature=0.8,
    max_tokens=4000
)

class SearchTool(BaseTool):
    name: str = "Search"
    description: str = "Search the internet for information"
    
    def _run(self, query: str) -> str:
        try:
            search_tool = DuckDuckGoSearchRun()
            result = search_tool.run(query)
            print(f"검색 쿼리: {query}")
            print(f"검색 결과 일부: {result[:200]}...")
            return result
        except Exception as e:
            print(f"검색 중 에러 발생: {e}")
            return str(e)

def create_agents():
    print("에이전트 생성 시작...")
    search_tool = SearchTool()
    
    site = Agent(
        role="한국 관광지 평가관",
        goal="사용자 요청에 맞춤형 관광지 코스 , 장소 , 주소 , 설명을 한다",
        backstory="대한민국 전체를 다니면서 관광지에 모르는게 없는 40년차 전문가",
        tools=[search_tool],
        llm=gpt,
        verbose=True
    )
    print("관광지 평가관 생성 완료")
    
    cafe = Agent(
        role="맛집,분위기좋은카페 평가관",
        goal="사용자 요청에 맞춤형 맛집,카페 코스 , 장소 , 주소 , 설명을 한다",
        backstory="대한민국 전체를 다니면서 맛집,카페 모르는게 없는 40년차 전문가",
        tools=[search_tool],
        llm=gpt,
        verbose=True
    )
    print("맛집/카페 평가관 생성 완료")

    accommodation = Agent(
        role="한국 숙소 평가관",
        goal="사용자 요청에 맞춤형 숙소 추천 , 장소 , 주소 , 설명을 한다",
        backstory="대한민국 전체를 다니면서 숙소에 모르는게 없는 40년차 전문가",
        tools=[search_tool],
        llm=gpt,
        verbose=True
    )
    print("숙소 평가관 생성 완료")

    pll = Agent(
        role="일정 생성 전문가",
        goal="사용자 요청에 맞춤형 관광지,맛집/카페,숙소 , 장소 , 주소 ,최적의 동선등을 고려해 시작날짜 끝나는날짜 안에 있는 일정계획을 전부 사용자 맞춤형으로 만들어준다",
        backstory="전세계 1등 여행 플래너 전문가 일정계획을 세우는데 최고의 전문가이다.",
        tools=[search_tool],
        llm=gpt,
        verbose=True
    )
    print("일정 생성 전문가 생성 완료")
    
    return site, accommodation, cafe, pll

def create_tasks(site, accommodation, cafe, pll, user_input):
    site_task = Task(
        description=f"""
        다음 조건에 맞는 관광지 추천 및 상세 정보 조사:
        입력 정보: {str(user_input)}

        다음 항목을 포함하여 상세하게 조사해주세요:
        1. 각 관광지별 정보:
        - 정식 명칭
        - 정확한 주소
        - 운영 시간
        - 입장료/이용료
        - 주요 볼거리 및 특징 (최소 3가지)
        - 추천 이유
        - 예상 소요 시간
        - 주변 교통편
        2. 최소 시간대별 3-4개의 관광지 추천
        3. 각 장소간 이동 시간과 최적 이동 수단
        4. 반려동물 동반 가능 여부
        5. 특별 주의사항이나 꿀팁
        """,
        agent=site,
        expected_output="관광지 목록과 모든 상세 정보를 구조화된 형식으로 제공"
    )

    cafe_task = Task(
        description=f"""
        다음 조건에 맞는 맛집과 카페 추천:
        입력 정보: {str(user_input)}

        다음 항목을 포함하여 상세하게 조사해주세요:
        1. 각 맛집/카페별 정보:
        - 상호명
        - 정확한 주소
        - 영업 시간
        - 대표 메뉴 (최소 3가지, 가격 포함)
        - 특징 및 분위기
        - 예약 필요 여부
        - 반려동물 동반 가능 여부
        2. 시간대별로 최소 3-4곳 추천
        3. 각 식당의 예상 대기 시간
        4. 인근 관광지와의 거리
        5. 특별 메뉴나 할인 정보
        """,
        agent=cafe,
        expected_output="맛집/카페 목록과 모든 상세 정보를 구조화된 형식으로 제공",
        context=[site_task]
    )

    accommodation_task = Task(
        description=f"""
        다음 조건에 맞는 숙소 추천:
        입력 정보: {str(user_input)}

        다음 항목을 포함하여 상세하게 조사해주세요:
        1. 각 숙소별 정보:
        - 숙소명
        - 정확한 주소
        - 객실 종류 및 가격
        - 주요 시설 및 서비스
        - 체크인/아웃 시간
        - 반려동물 동반 가능 여부
        - 주차 가능 여부
        2. 최소 5개의 숙소 추천
        3. 인근 관광지/맛집과의 거리
        4. 교통 접근성
        5. 특별 패키지나 프로모션 정보
        """,
        agent=accommodation,
        expected_output="숙소 목록과 모든 상세 정보를 구조화된 형식으로 제공",
        context=[site_task, cafe_task]
    )

    planning_task = Task(
        description=f"""
        다음 조건에 맞는 상세 일정 계획 수립:
        입력 정보: {str(user_input)}

        다음 항목을 포함하여 상세하게 계획해주세요:
        1. 날짜별, 시간대별 상세 일정:
        - 30분 단위로 세분화된 일정
        - 각 장소별 소요 시간
        - 이동 시간 및 교통수단
        - 예상 비용
        2. 각 일정별:
        - 정확한 장소명과 주소
        - 예약 필요 사항
        - 추천 동선
        - 우천시 대체 일정
        3. 일자별 동선 최적화 계획
        4. 전체 예상 비용 계산
        5. 일정별 주의사항 및 팁
        """,
        agent=pll,
        expected_output="상세 일정표와 모든 부가 정보를 구조화된 형식으로 제공",
        context=[site_task, cafe_task, accommodation_task]
    )

    return site_task, cafe_task, accommodation_task, planning_task
def main():
    print("프로그램 시작...")
    
    user_input = {
      "location": "서울 강남",
      "start_date": "2025-01-24",
      "end_date": "2025-01-26",
      "age": "30대",
      "companions": {
        "adults": 2,
        "teens": 1,
        "pets": 1
      },

      
      "concepts": [
        "미식 여행",
        "호캉스"
      ]
    }
    
    print(f"사용자 입력값: {user_input}")

    try:
        # 에이전트 생성
        site, accommodation, cafe, pll = create_agents()
        
        # 태스크 생성
        site_task, cafe_task, accommodation_task, planning_task = create_tasks(
            site, accommodation, cafe, pll, user_input
        )

        # Crew 생성 및 실행
        print("Crew 생성 및 실행 시작...")
        crew = Crew(
            agents=[site, cafe, accommodation, pll],
            tasks=[site_task, cafe_task, accommodation_task, planning_task],
            verbose=True
        )
        
        print("작업 실행 시작...")
        result = crew.kickoff()
        print("\n=== 최종 여행 계획 결과 ===")
        print(result)
        
    except Exception as e:
        print(f"에러 발생: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    print("스크립트 시작...")
    main()
    print("스크립트 종료...")