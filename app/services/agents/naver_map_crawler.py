from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import asyncio
import aiohttp       
import emoji
from crewai.tools import BaseTool
from typing import Any
import json
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field

# 크롤링 시간 11초(75개) -> 9.7초(20개) -> time.sleep() 5초에서 1초로 변경 -> 5.8초
def cafe_list_crawler(query):
    """
    동적 크롤링을 이용해 네이버 지도에서 카페를 검색하고 기본 정보를 가져오는 도구.
    """
    # 크롬 드라이버 설정
    options = webdriver.ChromeOptions()
    # options.add_experimental_option("detach", True)  # 창이 자동으로 닫히지 않게 설정
    options.add_argument("--headless")
    options.add_argument("user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Mobile Safari/537.36")
    driver = webdriver.Chrome(options=options)
    
    url = f"https://m.map.naver.com/search2/search.naver?query={query}"
    driver.get(url)

    # JavaScript가 실행되어 리스트가 생성될 때까지 기다림
    spots = WebDriverWait(driver, 10).until(
        EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "li._lazyImgContainer")))

    # time.sleep(1)  # (삭제하면 15개만 가져옴, 1초하면 될때도 있고 안될때도 있음)
    # 특정 클래스의 <li> 태그 가져오기
    # spots = driver.find_elements(By.CSS_SELECTOR, "li._lazyImgContainer")
    spots_info = []

    for spot in spots:
        if len(spots_info) >= 20:  # 20개까지만 수집
            break
        place_id = spot.get_attribute("data-id")
        map_url = f"https://m.place.naver.com/restaurant/{place_id}/location?filter=location&selected_place_id={place_id}"
        url = f"https://m.place.naver.com/restaurant/{place_id}/home"
        # 테스트 : https://m.place.naver.com/restaurant/1932943275/location?reviewSort=recent&filter=location&selected_place_id=1932943275

        spot_info = {
            "place_id": place_id,
            "kor_name": spot.get_attribute("data-title"),
            "address": spot.find_element(By.CLASS_NAME, "item_address").text.strip().replace("주소보기\n", ""),
            "url": url,
            "image_url": spot.find_element(By.CLASS_NAME, "_itemThumb").find_element(By.TAG_NAME, "img").get_attribute("src"),
            "map_url" : map_url,
            "latitude": spot.get_attribute("data-latitude"),
            "longitude": spot.get_attribute("data-longitude"),
            "phone_number": spot.get_attribute("data-tel")
        }
        spots_info.append(spot_info)

    driver.quit()
    print(f"가져온 카페 개수: {len(spots_info)}")
    return spots_info

# 리뷰 가져오는 스크래퍼
# 동기로 실행했을때 93초, 변경 후 8.41초 !!
# 75개 리스트 (8.41초) -> 20개 (5.8초)
async def fetch_review(session, place_id):
    """
    비동기 리뷰 스크래퍼. 네이버 지도에서 카페를 정적 크롤링을 통해 검색하고 리뷰를 가져오는 도구.
    """
    url = f"https://m.place.naver.com/restaurant/{place_id}/review/visitor?reviewSort=recent"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
        "Referer": "https://m.place.naver.com/"
    }
    
    async with session.get(url, headers=headers) as response:
        if response.status != 200:
            print(f"{place_id} 요청 실패: {response.status}")
            return {"place_id": place_id, "reviews": []}

        html = await response.text()
        soup = BeautifulSoup(html, "html.parser")
        reviews = soup.find_all("div", class_="pui__vn15t2")
        reviews_list = [emoji.replace_emoji(review.text, replace='') for review in reviews]
        # print(len(reviews_list)) #10개 리뷰
        return {
            "place_id": place_id,
            "reviews": reviews_list
        }


async def fetch_all_reviews(place_id_list):
    """
    async를 사용하여 모든 place_id를 병렬 처리 
    """
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_review(session, place_id) for place_id in place_id_list]
        return await asyncio.gather(*tasks)  # 모든 요청을 동시에 실행


class QuerySchema(BaseModel):
    query: str = Field(
        ..., description="여행 지역, 취향 등 조건이 포함된 카페 검색어"
    )
    
class GetCafeInfoTool(BaseTool):
    """네이버 크롤링을 통해 카페 정보 수집"""
    name: str = "get_cafe_info"
    description: str = "네이버 지도에서 카페 정보를 검색하고 리뷰를 가져오는 CrewAI 도구"
    args_schema: Type[BaseModel] = QuerySchema
    
    async def _run(self, query: str) -> str:
        """
        CrewAI에서 사용할 수 있도록 비동기 크롤링을 수행하는 도구.
        """
        start_time = datetime.now()

        # 동기 크롤링 실행
        cafes_info = cafe_list_crawler(query)
        place_id_list = [cafe["place_id"] for cafe in cafes_info]

        # 비동기 리뷰 크롤링 실행
        reviews = await fetch_all_reviews(place_id_list)
        
        end_time = datetime.now()
        print(f"정보 수집 시간: {(end_time - start_time).total_seconds()}초")

        return json.dumps({
            "cafe_info": cafes_info,
            "reviews": reviews
        }, ensure_ascii=False)
   

    async def run(self, *args, **kwargs):
        """CrewAI에서 실행될 때 자동으로 await _run()이 실행되도록 수정"""

        return await self._run(*args, **kwargs)
        # if asyncio.get_event_loop().is_running():
        #     return asyncio.ensure_future(self._run(*args, **kwargs))
        # else:
        #     loop = asyncio.new_event_loop()
        #     asyncio.set_event_loop(loop)

        #     return loop.run_until_complete(self._run(*args, **kwargs))