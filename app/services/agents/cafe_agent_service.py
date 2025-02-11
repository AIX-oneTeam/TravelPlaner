from crewai import Agent, Task, Crew, LLM, Process
from crewai_tools import SerperDevTool, WebsiteSearchTool
from app.services.agents.cafe_tool import GoogleMapSearchTool, NaverLocalSearchTool,MultiToolWrapper
from app.services.agents.travel_all_schedule_agent_service import spots_pydantic, calculate_trip_days

import os
from dotenv import load_dotenv
import traceback
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

search_dev_tool = SerperDevTool()
google_map_tool = GoogleMapSearchTool()
naver_local_tool = NaverLocalSearchTool()
multi_tool=MultiToolWrapper(google_map_tool,naver_local_tool) 


# LLM 초기화
my_llm = LLM(
    model="gpt-4o-mini",
    api_key=OPENAI_API_KEY,
    temperature=0,
    max_tokens=4000
)

async def cafe_agent(user_input, user_prompt=""):
    """
    CrewAI를 실행하여 사용자 맞춤 카페를 추천해주는 서비스.
    """
    
    if user_input is None:
        raise ValueError("user_input이 없습니다. 잘못된 요청을 보냈는지 확인해주세요")
    
    user_input["concepts"] = ', '.join(user_input.get('concepts',''))
    user_input["user_prompt"] = user_prompt
    user_input["n"] = calculate_trip_days(user_input.get('start_date',''),user_input.get('end_date',''))*2
    
    try:

        # 에이전트 정의
        researcher = Agent(
            role="카페 정보 검색 및 분석 전문가",
            goal="고객 선호도를 분석해 최적의 카페 정보 수집 후 각 카페의 주요 특징 분석",
            backstory="""
            사용자의 여행을 특별하게 만들기 위해, 최적의 카페를 찾고 카페의 매력을 심층 분석하여 사용자가 최적의 선택을 할 수 있도록 하세요.
            """,
            tools=[search_dev_tool],
            allow_delegation=False,
            # max_iter=1,
            llm=my_llm,
            verbose=True
        )

        checker = Agent(
            role="카페 검증 전문가",
            goal="researcher가 분석한 데이터를 기반으로 정보를 수집하고 입력하세요.",
            backstory="resercher가 준 카페리스트를 토대로 정확한 정보를 찾아주세요",
            # max_iter=1,
            allow_delegation=False,
            tools=[multi_tool],
            llm=my_llm,
            verbose=True
        )

        # 태스크 정의
        researcher_task = Task(
            description="""
            고객이 최고의 여행을 할 수 있도록 고객의 상황과 취향에 맞는 카페를 고르기 위해 최소한 서로 다른 {n}곳 이상의 카페를 조사하고 최종적으로 {n}개의 카페 정보를 반환해주세요.

            정보는 최신정보(2024년 1월 1일 이후 작성된 정보)를 기준으로 작성해주세요.
            카페는 반드시 고객의 여행 지역인 {main_location}에 위치해야하고, 폐업 또는 휴업하지 않은 카페여야합니다. 
            고객의 선호도({concepts})와, 주 연령대({ages})와 요구사항({user_prompt})을 반영해 카페를 찾아주세요.
            고객의 선호도({concepts})와 요구사항({user_prompt})에 "프랜차이즈"가 포함되지 않는 경우, 프랜차이즈 카페는 제외해주세요.
            프랜차이즈 카페 : 스타벅스, 투썸플레이스, 이디야, 빽다방, 메가커피 등 전국에 매장이 5개 이상인 커피 전문점 
            협찬을 받거나 음료 및 음식을 무료로 제공받아 작성한 포스팅, 광고글은 제외하고 조사해주세요.
            해당 여행지를 방문한 사람이라면 꼭 방문하는 카페가 있다면 우선적으로 선택해주세요.   
            
            시그니처 메뉴는 "다양한"과 같은 모호하고 추상적인 단어를 사용하지 않고 구체적인 메뉴의 이름을 명시해주세요.
            description에는 카페의 최신 리뷰와 사진을 분석해 해당 카페의 분위기, 시그니처 메뉴, 사람들이 공통적으로 좋아했던 주요 특징을 간략히 적어주세요.
            description에는 절대 나이, 연령대에 대한 언급을 하지마세요.
            
            모르는 정보는 지어내지 말고 "정보 없음"으로 작성하세요. 
            반드시 서로 다른 {n}개의 카페를 반환해주세요.
            """,
            expected_output="""
            {n}개의 카페 리스트를 텍스트 형태로 반환해주세요.
            - kor_name : "카페 이름"
            - description : "카페 설명"
            - address : "카페 주소"
            """,
            output_json=spots_pydantic,
            agent=researcher
        )

        checker_task = Task(
            description="""
            researcher가 반환한 카페들의 kor_name + {main_location}을 검색해 spots_pydantic에 필요한 정보를 수집하세요.
            모르는 정보는 지어내지 말고 "정보 없음"으로 작성하세요. 
            """,
            expected_output="""
            다음 4가지 필드는 항상 해당 값으로 고정해주세요
            spot_category: 3
            order: 0
            day_x: 0
            spot_time: null
            """,
            output_json=spots_pydantic,
            agent=checker
        )


        # 멀티 에이전트 시스템 설정
        crew = Crew(
            agents=[researcher, checker],
            tasks=[researcher_task, checker_task],
            process=Process.sequential,
            verbose=True,
        )

        # 실행
        try:
            crew.kickoff(inputs=user_input)
            final_pydantic_output = checker_task.output_pydantic
            final_dict = final_pydantic_output.model_dump()
            return final_dict
        except Exception as e:
            print(f"Error during execution: {e}")

            # 오류가 발생한 경우 Observation을 직접 확인
            if hasattr(e, 'Observation'):
                print(f"Tool Output (Observation): {e.Observation}")
    except Exception as e:
        print(f"[ERROR] {e}")
        traceback.print_exc()
        return {"message": "요청 처리 중 오류가 발생했습니다.", "error": str(e)}

                        
if __name__ == "__main__":
    user_input = {
    "ages" : "30대",
    "companion_count": [{"label":"성인", "count": 2},{"label":"영유아", "count": 1}],
    "start_date":"2025-02-18",  
    "end_date":"2025-02-20",
    "concepts":["조용한", "베이글"], 
    "main_location":"서울특별시 강남구"
    }
    
    agent_result = cafe_agent(user_input)
    print(f"------------------------")
    print(f"type of agent_result : {type(agent_result)}")
    print(f"------------------------")
    print(f"result of agent_result : {agent_result}")
    
    
# 방법 1 :구글 검색 > 나온 카페들 지도에서 정보 검색(카페별로 1번씩)
# 방법 2 :지도 검색 > 나온 카페들 후기 검색(카페별로 1번씩) 