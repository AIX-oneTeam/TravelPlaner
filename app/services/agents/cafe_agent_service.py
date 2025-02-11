from typing import List
from crewai import Agent, Task, Crew, LLM, Process
from app.dtos.spot_models import spots_pydantic,calculate_trip_days
from app.services.agents.naver_map_crawler import GetCafeListTool, GetCafeBusinessTool
from app.services.agents.travel_all_schedule_agent_service import spots_pydantic, calculate_trip_days
from pydantic import BaseModel
import os
from dotenv import load_dotenv
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        
class CafeAgentService:
    """
    카페 에이전트 인스턴스를 싱글톤 패턴으로 관리하는 클래스
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CafeAgentService, cls).__new__(cls)
            cls._instance.initialize()  # 최초 한 번만 초기화
        return cls._instance  # 동일한 인스턴스 반환

    def initialize(self):
        """CrewAI 관련 객체들을 한 번만 생성"""
        print("cafe agent를 초기화합니다")
                
        self.llm = LLM(
            model="gpt-4o-mini",
            api_key=OPENAI_API_KEY,
            temperature=0,
            max_tokens=4000
        )
        self.get_cafe_list_tool = GetCafeListTool()
        self.get_cafe_business_tool = GetCafeBusinessTool()

        # 에이전트 정의
        self.researcher = Agent(
            role="카페 정보 검색 및 분석 전문가",
            goal="고객 선호도를 분석해 최적의 카페를 찾을 수 있는 검색어를 추출하고, 정보 수집 후 각 카페의 주요 특징 분석",
            backstory="""
            사용자의 여행을 특별하게 만들기 위해, 최적의 카페를 찾고 카페의 매력을 심층 분석하여 사용자가 최적의 선택을 할 수 있도록 하세요.
            """,
            tools=[self.get_cafe_list_tool],
            allow_delegation=False,
            max_iter=1,
            llm=self.llm,
            verbose=True,
            stop_on_failure=True
        )
        
        self.checker = Agent(
        role="카페 검증 전문가",
        goal="researcher가 분석한 데이터를 기반으로 정보를 수집하고 입력하세요.",
        backstory="resercher가 준 카페리스트를 토대로 정확한 정보를 찾아주세요",
        max_iter=1,
        allow_delegation=False,
        tools=[self.get_cafe_business_tool],
        llm=self.llm,
        verbose=True,
    )
        self.crew = None   
        
    async def cafe_agent(self, user_input, user_prompt=""):
        """
        CrewAI를 실행하여 사용자 맞춤 카페를 추천하는 서비스
        """
        if user_input is None:
            raise ValueError("user_input이 없습니다. 잘못된 요청을 보냈는지 확인해주세요")
        
        user_input["concepts"] = ', '.join(user_input.get('concepts',''))
        user_input["user_prompt"] = user_prompt
        user_input["n"] = calculate_trip_days(user_input.get('start_date',''),user_input.get('end_date',''))*2
        
        # 태스크 정의(user_input에 다라 값이 바뀌므로 __init__밖에 설정)
        researcher_task = Task(
            description="""
            주요 목표:
            - {main_location} 지역의 카페 {n}개 선정
            - 고객 선호도: {concepts}
            - 특별 요구사항: {user_prompt}
            - 주 연령대: {ages}

            분석 요구사항:
            1. 카페 특징 분석
            2. 주요 메뉴 확인
            3. 긍정적 리뷰 중심 분석
            
            tool 사용시 "{main_location} 카페"로 검색
            반드시 서로 다른 이름의 {n}개의 카페를 반환해주세요.
            모르는 정보는 지어내지 말고 "정보 없음"으로 작성하세요.
            """,
            expected_output="""
            다음과 같은 형식으로 데이터를 반환하세요.
            rank: "추천 우선순위" 
            reason: "해당 우선순위를 정한 이유, 다른 카페들보다 추천하는 이유"
            place_id: "네이버 place_id"
            kor_name: "카페 이름"
            description: "카페 주요 특징 및 시그니처 메뉴"
            address: "주소"
            url: "홈페이지 주소"
            image_url: "이미지 주소" 
            map_url: "지도 주소"
            latitude: "위도" 
            longitude: "경도" 
            phone_number: "전화번호"
            """,        
            agent=self.researcher
        )

        checker_task = Task(
            description="""
            researcher가 반환한 카페들의 정보에 추가로 운영시간, 웹사이트 정보를 수집하고 수정해주세요.
            tool 사용시 입력값은 researcher가 반환한 카페들의 place_id들을 묶어 list형태로 변환해 입력해주세요.
            """,
            expected_output="""
            모르는 정보는 지어내지 말고 "정보 없음"으로 작성하세요. 
            """,
            context=[researcher_task],
            output_json=spots_pydantic,
            agent=self.checker
        )


        # 멀티 에이전트 시스템 설정
        crew = Crew(
            agents=[self.researcher, self.checker],
            tasks=[researcher_task, checker_task],
            process=Process.sequential,
            verbose=True,
            context=[researcher_task]  
        )

        # 실행
        try:
            result = await crew.kickoff_async(inputs=user_input)
            print(result)
            return result.json_dict.get("spots",[])
        except Exception as e:
            print(f"Error during execution: {e}")

            # 오류가 발생한 경우 Observation을 직접 확인
            if hasattr(e, 'Observation'):
                print(f"Tool Output (Observation): {e.Observation}")