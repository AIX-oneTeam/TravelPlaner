from crewai import Agent, Task, Crew, LLM, Process
from crewai_tools import SerperDevTool
from app.services.agents.naver_map_crawler import GetCafeInfoTool
from app.services.agents.travel_all_schedule_agent_service import spots_pydantic, calculate_trip_days

import os
from dotenv import load_dotenv
import traceback
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

search_dev_tool = SerperDevTool()
get_cafe_tool = GetCafeInfoTool()
# get_cafe_tool._run("강남구 조용한 카페")

# LLM 초기화
my_llm = LLM(
    model="gpt-4o-mini",
    api_key=OPENAI_API_KEY,
    temperature=0,
    max_tokens=4000
)

def cafe_agent(user_input, user_prompt=""):
    """
    CrewAI를 실행하여 사용자 맞춤 카페를 추천해주는 서비스.
    """
    
    if user_input is None:
        raise ValueError("user_input이 없습니다. 잘못된 요청을 보냈는지 확인해주세요")
    
    user_input["concepts"] = ' '.join(user_input.get('concepts',''))
    user_input["user_prompt"] = user_prompt
    user_input["n"] = calculate_trip_days(user_input.get('start_date',''),user_input.get('end_date',''))*2
    
    try:

        # 에이전트 정의
        researcher = Agent(
            role="카페 정보 검색 및 분석 전문가",
            goal="고객 선호도를 분석해 최적의 카페를 찾을 수 있는 검색어를 추출하고, 정보 수집 후 각 카페의 주요 특징 분석",
            backstory="""
            사용자의 여행을 특별하게 만들기 위해, 최적의 카페를 찾고 카페의 매력을 심층 분석하여 사용자가 최적의 선택을 할 수 있도록 하세요.
            """,
            tools=[get_cafe_tool],
            allow_delegation=False,
            max_iter=2,
            llm=my_llm,
            verbose=True
        )

        checker = Agent(
            role="카페 검증 전문가",
            goal="researcher가 분석한 데이터를 기반으로 정보를 수집하고 입력하세요.",
            backstory="resercher가 준 카페리스트를 토대로 정확한 정보를 찾아주세요",
            # max_iter=1,
            allow_delegation=False,
            tools=[search_dev_tool],
            llm=my_llm,
            verbose=True
        )

        # 태스크 정의
        researcher_task = Task(
            description="""
            고객이 최고의 여행을 할 수 있도록 고객의 상황과 취향에 맞는 카페를 고르기 위해 카페를 조사하고 최종적으로 고객의 needs를 만족하는 {n}개의 카페 정보를 반환해주세요.
            tool 사용시 검색어는 "지역 이름 + 선호 또는 요구사항(" "를 기준으로 구분하여 1개 또는 2개 선택) + 카페"로 입력해주세요
            tool output을 참고하여 카페의 특징을 분석하고 description을 작성해주세요
            description에는 카페의 리뷰를 분석해 사람들이 공통적으로 좋아했던 카페의 주요 특징과 메뉴 이름을 포함해 간략히 적어주세요.
            description에는 절대 나이, 연령대에 대한 언급을 하지마세요.
            
            카페는 반드시 고객의 여행 지역인 {main_location}에 위치해야하고, 폐업 또는 휴업하지 않은 카페여야합니다. 
            고객의 선호도({concepts})와, 주 연령대({ages})와 요구사항({user_prompt})을 반영해 카페를 찾아주세요.
            고객의 선호도({concepts})와 요구사항({user_prompt})에 "프랜차이즈"가 포함되지 않는 경우, 프랜차이즈 카페는 제외해주세요.
            프랜차이즈 카페 : 스타벅스, 투썸플레이스, 이디야, 빽다방, 메가커피 등 전국에 매장이 5개 이상인 커피 전문점 
            
            모르는 정보는 지어내지 말고 "정보 없음"으로 작성하세요. 
            """,
            expected_output="""
            반드시 서로 다른 이름의 {n}개의 카페를 반환해주세요.  
            다음 4가지 필드는 항상 해당 값으로 고정해주세요
            spot_category: 3
            order: 0
            day_x: 0
            spot_time: null 
            """,
            output_json=spots_pydantic,            
            agent=researcher
        )

        checker_task = Task(
            description="""
            researcher가 반환한 카페들의 정보 중 spots_pydantic에 필요한 추가 정보를 수집하고 수정해주세요.
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
            agents=[researcher],
            tasks=[researcher_task],
            process=Process.sequential,
            verbose=True,
        )

        # 실행
        try:
            result = crew.kickoff(inputs=user_input)
            print(result)
            return result
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
    
