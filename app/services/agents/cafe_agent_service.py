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

class CafeReasearcherOutput(BaseModel):
    rank: int 
    reason: str 
    place_id: str
    kor_name: str
    description: str 
    address: str 
    url: str 
    image_url: str 
    map_url: str 
    latitude: float 
    longitude: float 
    phone_number: str
    
class CafeReasearcherOutputList(BaseModel):
    cafe_list: list[CafeReasearcherOutput]
        
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
            고객이 최고의 여행을 할 수 있도록 고객의 상황과 취향에 맞는 카페를 고르기 위해 카페를 조사하고 최종적으로 고객의 needs를 만족하는 {n}개의 카페 정보를 반환해주세요.
            tool 사용시 검색어는 "{main_location} 카페"를 입력해주세요

            tool output을 참고하여 카페의 특징을 분석하고 description을 작성해주세요
            description에는 카페의 리뷰를 분석해 사람들이 공통적으로 좋아했던 카페의 주요 특징과 메뉴 이름을 포함해 간략히 적어주세요.
            description에는 절대 나이, 연령대에 대한 언급을 하지마세요.
            
            카페는 반드시 고객의 여행 지역인 {main_location}에 위치해야하고, 폐업 또는 휴업하지 않은 카페여야합니다. 
            고객의 선호도({concepts})와 요구사항({user_prompt})에 "프랜차이즈"가 포함되지 않는 경우, 프랜차이즈 카페는 제외해주세요.
            프랜차이즈 카페 : 스타벅스, 투썸플레이스, 이디야, 빽다방, 메가커피 등 전국에 매장이 5개 이상인 커피 전문점 
 
            {n}개의 카페를 선정시 고객의 요구사항({user_prompt}), 여행 컨셉({concepts}), 주 연령대({ages})를 우선적으로 반영해주세요.    
            부정적인 의견이 있으면 선택하지 마세요.
            rank에는 추천 우선 순위를 적어주세요.
            reason에는 해당 우선순위를 준 이유와, 다른 카페들을 선택하지 않고, 해당 카페를 선택한 이유를 적어주세요. 
            모르는 정보는 지어내지 말고 "정보 없음"으로 작성하세요. 
            """,
            expected_output="""
            반드시 서로 다른 이름의 {n}개의 카페를 반환해주세요.
            """,        
            agent=self.researcher,
            output_json=CafeReasearcherOutputList,
        )

        checker_task = Task(
            description="""
            researcher가 반환한 카페들의 정보에 추가로 운영시간, 웹사이트 정보를 수집하고 수정해주세요.
            모르는 정보는 지어내지 말고 "정보 없음"으로 작성하세요. 
            tool 사용시 입력값은 researcher가 반환한 카페들의 place_id들을 묶어 list형태로 변환해 입력해주세요.
            """,
            expected_output="""
            반드시 서로 다른 이름의 {n}개의 카페를 반환해주세요.  
            다음 4가지 필드는 항상 해당 값으로 고정해주세요
            spot_category: 3
            order: 0
            day_x: 0
            spot_time: null 
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