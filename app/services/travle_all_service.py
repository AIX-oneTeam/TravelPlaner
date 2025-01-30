import os
import json
import requests
import traceback
from typing import Optional
from dotenv import load_dotenv

from datetime import datetime

# crewAI 관련
from crewai import Agent, Task, Crew, LLM
from crewai.tools import BaseTool

############################################################################
# 0. Load environment variables
############################################################################
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

############################################################################
# 1. Naver Web Search Tool (일반 텍스트 검색)
############################################################################
class NaverWebSearchTool(BaseTool):
    name: str = "NaverWebSearch"
    description: str = "네이버 웹 검색 API를 사용해 텍스트 정보를 검색"

    def _run(self, query: str) -> str:
        if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
            return "[NaverWebSearchTool] 네이버 API 자격 증명이 없습니다."

        url = "https://openapi.naver.com/v1/search/webkr"
        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
        }
        params = {
            "query": query,
            "display": 3,
            "start": 1,
            "sort": "sim"
        }

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


############################################################################
# 2. Naver Local Search Tool (정확한 주소)
############################################################################
class NaverLocalSearchTool(BaseTool):
    """
    네이버 지역 검색(Local Search) API를 사용하여
    실제 주소(roadAddress 등)를 가져옴
    """
    name: str = "NaverLocalSearch"
    description: str = "네이버 지역 검색 API로부터 장소 주소 등을 가져옴"

    def _run(self, query: str) -> str:
        if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
            return "[NaverLocalSearchTool] 네이버 API 자격 증명이 없습니다."

        url = "https://openapi.naver.com/v1/search/local.json"
        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
        }
        params = {
            "query": query,
            "display": 1,
            "sort": "sim"
        }

        try:
            resp = requests.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

            items = data.get("items", [])
            if not items:
                return "[]"

            item = items[0]
            # title, address, roadAddress, mapx, mapy 등을 JSON화
            # 주의: title에 <b></b> 태그가 있을 수 있음 → 제거할 수도 있음
            return json.dumps({
                "title": item.get("title", ""),
                "category": item.get("category", ""),
                "address": item.get("address", ""),
                "roadAddress": item.get("roadAddress", ""),
                "mapx": item.get("mapx", ""),
                "mapy": item.get("mapy", "")
            }, ensure_ascii=False)

        except Exception as e:
            return f"[NaverLocalSearchTool] 에러: {str(e)}"


############################################################################
# 3. Naver Image Search Tool (이미지)
############################################################################
class NaverImageSearchTool(BaseTool):
    name: str = "NaverImageSearch"
    description: str = "네이버 이미지 검색 API를 사용하여 이미지 URL을 가져옴"

    def _run(self, query: str) -> str:
        if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
            return "[NaverImageSearchTool] 네이버 API 자격 증명이 없습니다."

        url = "https://openapi.naver.com/v1/search/image"
        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
        }
        params = {
            "query": query,
            "display": 1,
            "sort": "sim"
        }

        try:
            resp = requests.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

            items = data.get("items", [])
            if not items:
                return ""
            return items[0].get("link", "")

        except Exception as e:
            return f"[NaverImageSearchTool] 에러: {str(e)}"


############################################################################
# 4. LLM (OpenAI GPT, via crewAI)
############################################################################
def get_llm():
    return LLM(
        api_key=OPENAI_API_KEY,
        model="gpt-4o-mini",
        temperature=0
    )

############################################################################
# 5. 날짜 계산 유틸
############################################################################
def calculate_trip_days(start_date_str, end_date_str):
    fmt = "%Y-%m-%d"
    start_dt = datetime.strptime(start_date_str, fmt)
    end_dt = datetime.strptime(end_date_str, fmt)
    delta = end_dt - start_dt
    return delta.days + 1

############################################################################
# 6. 에이전트 생성 (site, cafe, accom, plan)
############################################################################
def create_agents():
    llm = get_llm()
    web_search_tool = NaverWebSearchTool()

    site_agent = Agent(
        role="관광지 평가관",
        goal="사용자 location 주변 관광지 정보",
        backstory="전국 관광지 마스터",
        tools=[web_search_tool],
        llm=llm,
        verbose=True
    )

    cafe_agent = Agent(
        role="맛집/카페 평가관",
        goal="사용자 location 주변 맛집/카페 정보",
        backstory="전국 맛집/카페 마스터",
        tools=[web_search_tool],
        llm=llm,
        verbose=True
    )

    accommodation_agent = Agent(
        role="숙소 평가관",
        goal="사용자 location 주변 숙소 정보",
        backstory="전국 숙소 마스터",
        tools=[web_search_tool],
        llm=llm,
        verbose=True
    )

    planning_agent = Agent(
        role="일정 생성 전문가",
        goal="사용자 location 주변 장소로 일정 생성",
        backstory="베테랑 여행 플래너",
        tools=[web_search_tool],
        llm=llm,
        verbose=True
    )

    return site_agent, cafe_agent, accommodation_agent, planning_agent

############################################################################
# 7. Tasks: site, cafe, accom, plan
############################################################################
def create_tasks(site_agent, cafe_agent, accommodation_agent, planning_agent, user_input):
    trip_days = calculate_trip_days(user_input["start_date"], user_input["end_date"])
    location = user_input["location"]

    site_task = Task(
        description=f"""
        [관광지 정보 조사]
        - '{location}' 인근의 관광지(spot_category=4) 최소 5곳
        - 주소, 운영시간, 입장료, 특징, 추천 이유, 반려동물 가능
        """,
        agent=site_agent,
        expected_output="관광지 목록 (텍스트)"
    )

    cafe_task = Task(
        description=f"""
        [맛집/카페 조사]
        - '{location}' 인근 맛집(spot_category=2) 5+, 카페(spot_category=3) 3+
        - 주소, 영업시간, 대표메뉴, 예약 여부, 반려동물 가능
        """,
        agent=cafe_agent,
        context=[site_task],
        expected_output="맛집,카페 목록 (텍스트)"
    )

    accommodation_task = Task(
        description=f"""
        [숙소 조사]
        - '{location}' 인근 숙소(spot_category=1) 5+
        - 주소, 객실, 시설, 체크인/아웃, 반려동물, 주차
        """,
        agent=accommodation_agent,
        context=[site_task, cafe_task],
        expected_output="숙소 목록 (텍스트)"
    )

    planning_task = Task(
        description=f"""
        [최종 일정 JSON 생성]
        - location: {location}
        - 여행기간: {user_input['start_date']} ~ {user_input['end_date']} (총 {trip_days}일)
        - 매일 (day_x): 맛집 3곳(아침/점심/저녁), 카페 2곳, 관광지 3곳, 숙소 1곳
        - Spots 필드:
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
            "business_status": true,
            "business_hours": "string",
            "order": 0,
            "day_x": 0,
            "spot_time": "2025-06-01T06:27:43.593Z"
          }}
        """,
        agent=planning_agent,
        context=[site_task, cafe_task, accommodation_task],
        expected_output="Spots[] JSON"
    )

    return site_task, cafe_task, accommodation_task, planning_task

############################################################################
# 8. 주소 보정 에이전트 & 태스크 (NaverLocalSearch)
############################################################################
def create_address_agent_task():
    llm = get_llm()
    local_search_tool = NaverLocalSearchTool()

    address_agent = Agent(
        role="주소 보정 전문가",
        goal="Spots[] 각 kor_name으로 정확한 주소를 가져와 업데이트",
        backstory="지도 API 마스터",
        tools=[local_search_tool],
        llm=llm,
        verbose=True
    )

    address_task = Task(
        description="""
            [주소 보정]
            1) 입력(최종 일정 JSON)을 파싱
            2) Spots[] 각각에 대해:
               - kor_name(혹은 eng_name)으로 NaverLocalSearchTool 검색
               - address, roadAddress를 가져와 spot['address']로 갱신
               - zip은 우편번호가 없으므로 빈 문자열
            3) 전체 JSON 반환
        """,
        agent=address_agent,
        expected_output="주소가 보정된 최종 JSON"
    )

    return address_agent, address_task

############################################################################
# 9. 이미지 에이전트 & 태스크
############################################################################
def create_image_agent_task():
    llm = get_llm()
    image_search_tool = NaverImageSearchTool()

    image_agent = Agent(
        role="이미지 검색 전문가",
        goal="각 Spot 이름으로 이미지 검색 후 image_url에 넣음",
        backstory="이미지 큐레이터",
        tools=[image_search_tool],
        llm=llm,
        verbose=True
    )

    image_task = Task(
        description="""
            [이미지 삽입]
            1) 입력(최종 일정 JSON)을 파싱
            2) Spots[] 각 항목의 kor_name으로 이미지 검색
            3) spot["image_url"] = 검색 결과
            4) 전체 JSON 반환
        """,
        agent=image_agent,
        expected_output="image_url이 채워진 최종 JSON"
    )

    return image_agent, image_task

############################################################################
# 10. main() 함수
############################################################################
def main():
    print("=== 프로그램 시작 ===")

    user_input = {
      "location": "부산",
      "start_date": "2025-07-01",
      "end_date": "2025-07-03",
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
    print("[사용자 입력]", user_input)

    try:
        # 1) 에이전트 생성
        site_agent, cafe_agent, accommodation_agent, planning_agent = create_agents()

        # 2) 태스크 생성
        site_task, cafe_task, accommodation_task, planning_task = create_tasks(
            site_agent, cafe_agent, accommodation_agent, planning_agent, user_input
        )

        # 3) 주소 보정 에이전트/태스크
        address_agent, address_task = create_address_agent_task()
        # 주소 보정은 planning_task 이후 수행
        address_task.context = [planning_task]

        # 4) 이미지 에이전트/태스크
        image_agent, image_task = create_image_agent_task()
        # 이미지 삽입은 주소 보정 이후
        image_task.context = [address_task]

        # 5) Crew 생성
        crew = Crew(
            agents=[
                site_agent,
                cafe_agent,
                accommodation_agent,
                planning_agent,
                address_agent,
                image_agent
            ],
            tasks=[
                site_task,
                cafe_task,
                accommodation_task,
                planning_task,
                address_task,
                image_task
            ],
            verbose=True
        )

        print("[INFO] 작업 실행 시작...")
        final_result = crew.kickoff()

        print("\n=== 최종 JSON 결과 (주소 보정 + 이미지 포함) ===")
        print(final_result)

    except Exception as e:
        print(f"[ERROR] {e}")
        traceback.print_exc()

    print("=== 프로그램 종료 ===")


if __name__ == "__main__":
    main()
