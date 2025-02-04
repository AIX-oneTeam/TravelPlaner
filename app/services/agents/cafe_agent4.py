from crewai import Agent, Task, Crew, LLM, Process
from crewai_tools import SerperDevTool
from app.services.agents.cafe_tool import GoogleMapSearchTool, NaverLocalSearchTool,MultiToolWrapper
from pydantic import BaseModel,Field
from typing import List
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

class CafeSimple(BaseModel):
    kor_name: str =  Field(..., description="카페 이름")
    description: str =  Field(..., description="카페 주요 특징, 분위기, 시그니처 메뉴 요약")
    address: str =  Field(..., description="카페 도로명 주소(한글)")
    zip_code: str =  Field(..., description="카페 우편번호")
    business_hours: dict =  Field(..., description="운영 시간")
    parking: bool =  Field(..., description="주차 가능 여부")
    pet_friendly: bool =  Field(..., description="애견동반 가능 여부")
    
class Cafe(BaseModel):
    """ 카페 정보 """
    kor_name: str =  Field(..., description="카페 이름")
    eng_name: str =  Field(..., description="카페 이름 (영문)")
    description: str =  Field(..., description="카페 주요 특징, 분위기, 시그니처 메뉴 요약")
    address: str =  Field(..., description="카페 도로명 주소(한글)")
    zip_code: str =  Field(..., description="카페 우편번호")
    url: str =  Field(..., description="카페 대표 홈페이지 url")
    image_url: str =  Field(..., description="카페 썸네일 url")
    map_url: str =  Field(..., description="카페 지도 url(google, naver, kakao 중 택1)")
    latitude: str =  Field(..., description="카페 위도")
    longitude: str =  Field(..., description="카페 경도")
    phone_number: str =  Field(description="카페 전화번호")
    business_status: bool =  Field(..., description="폐업 여부 (True: 정상, False: 폐업/휴업)")
    business_hours: dict =  Field(..., description="운영 시간")
    parking: bool =  Field(..., description="주차 가능 여부")
    pet_friendly: bool =  Field(..., description="애견동반 가능 여부")

class CafeList(BaseModel):
    cafes: List[Cafe]
    
class CafeSimpleList(BaseModel):
    cafes: List[CafeSimple]


def cafe_agent(user_input):
    """
    CrewAI를 실행하여 사용자 맞춤 카페를 추천해주는 서비스.
    반환값은 JSON 형식
    """

    try:
        # location = user_input.get("location", "")
        # concepts = user_input.get("concepts", "")
        # age = user_input.get("main_location", "")
        # parking = user_input.get("main_location", "")
        # pet_friendly = user_input.get("main_location", "")

        # 에이전트 정의
        researcher = Agent(
            role="카페 정보 검색 및 분석 전문가",
            goal="고객 선호도를 분석해 최적의 카페 정보 수집 후 각 카페의 주요 특징 분석",
            backstory="""
            사용자의 여행을 특별하게 만들기 위해, 최적의 카페를 찾고 카페의 매력을 심층 분석하여 사용자가 최적의 선택을 할 수 있도록 돕는 전문가
            고객의 선호도 및 제약 사항(애견 동반 유무, 주차 등)을 반드시 반영해야 합니다.
            협찬을 받거나 광고성 글은 제외하고 조사해주세요.
            모르는 정보는 "정보 없음"으로 나타내세요.
            각 cafe는 모두 다른 곳으로 조사해주세요.
            """,
            tools=[search_dev_tool],
            allow_delegation=False,
            max_iter=3,
            llm=my_llm,
            verbose=True
        )

        checker = Agent(
            role="카페 검증 전문가",
            goal="researcher가 분석한 데이터를 기반으로 정보가 정확한지 검증하고, 수정하세요.",
            backstory="resercher가 찾지 못한 정보를 보완하고, 잘못 찾은 정보는 정확한 정보로 수정해주세요",
            # max_iter=2,
            allow_delegation=False,
            tools=[multi_tool],
            llm=my_llm,
            verbose=True
        )

        # 태스크 정의
        researcher_task = Task(
            description="""
            고객이 최고의 여행을 할 수 있도록 고객의 상황과 취향에 맞는 카페 3곳을 찾고 카페 정보를 반환해주세요.

            카페는 반드시 고객의 여행 지역인 {location}에 위치해야하고, 폐업 또는 휴업하지 않은 카페여야합니다. 
            고객의 선호도({concepts})와, 주 연령대({age}), 주차 가능 여부({parking})와 애견동반 여부({pet_friendly})를 반영해 카페를 찾아주세요.
            협찬을 받고 작성한 글이나 광고 글은 제외하고 조사해주세요.
            시그니처 메뉴는 "다양한"과 같은 추상적인 단어를 사용하지 않고 정확한 메뉴의 이름을 명시해주세요.
            description에는 카페의 최신 리뷰와 사진을 분석해 해당 카페의 분위기, 시그니처 메뉴, 사람들이 공통적으로 좋아했던 주요 특징을 간략히 적어주세요.
            description에는 나이, 연령대, 주차, 애견동반 여부에 대한 언급 하지마세요.
            모르는 정보는 지어내지 말고 "정보 없음"으로 작성하세요. 
            
            반드시 서로 다른 3곳의 카페를 반환해주세요.
            고객의 선호도({concepts})에 "프랜차이즈"가 포함되지 않는 경우, 프랜차이즈 카페는 3곳에서 제외해주세요.
            프랜차이즈 카페 : 스타벅스, 투썸플레이스, 이디야, 빽다방, 메가커피 등 전국에 매장이 5개 이상인 커피 전문점 
            """,
            expected_output="""
            3개의 카페 리스트를 json 형태로 반환해주세요.
            예시: {"cafes": [<Cafe1>, <Cafe2>, <Cafe3>]}
            """,
            output_json=CafeSimpleList,
            agent=researcher,
        )

        checker_task = Task(
            description="""
            researcher가 반환한 카페들의 kor_name + {location}을 검색해 Cafe에 필요한 정보들을 찾아 입력해주세요. 
            """,
            expected_output="""
            검증된 정확한 정보를 json 형태로 반환해주세요.
            예시: {"cafes": [<Cafe1>, <Cafe2>, <Cafe3>]}
            """,
            output_json=CafeList,
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
            result = crew.kickoff(inputs=user_input)
            # print(result.__dict__)
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
    "location":"석촌",  # 사용자의 지역
    "age" : "30대",
    "concepts":"조용한, 베이글",  # 취향
    "parking":True,  # 주차 가능 여부
    "pet_friendly":True  # 반려동물 동반 가능 여부
    }
                   
    agent_result = cafe_agent(user_input)
    print(f"------------------------")
    print(f"type of agent_result : {type(agent_result)}")
    print(f"------------------------")
    print(f"result of agent_result : {agent_result}")