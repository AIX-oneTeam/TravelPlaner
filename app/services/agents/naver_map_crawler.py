from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import asyncio
import aiohttp       
import emoji
from crewai.tools import BaseTool
from typing import Any
import json
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field

class WebDriver:
    _driver = None
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            if cls._driver is None:
                options = webdriver.ChromeOptions()
                options.add_argument("--headless") # 크롬창 안보이게
                # options.add_experimental_option("detach", True) # 확인용(크롬창 열림)
                options.add_argument("user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Mobile Safari/537.36")
                cls._driver = webdriver.Chrome(options=options)
        return cls._driver
         
def cafe_list_crawler(query):
    """
    네이버 지도에서 카페 정보를 크롤링하는 함수
    Args:
        query (str): 검색어
    Returns:
        list: 카페 정보 리스트
    """
    driver = WebDriver()
    spots_info = []
    
    try:
        url = f"https://m.map.naver.com/search2/search.naver?query={query}"
        driver.get(url)

        # 페이지 로딩 대기
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
      
        spots = WebDriverWait(driver, 10).until(
            EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "li._lazyImgContainer")))
        
        if not spots:  # 검색 결과가 없으면 예외를 발생시키지 않음 (정상적인 흐름)
            return "검색어를 변경해주세요"

        for spot in spots:
            # if len(spots_info) >= 15:  # 15개까지만 수집
            #     break
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
        
        print(f"가져온 카페 개수: {len(spots_info)}")
        return spots_info

    except Exception as e:
        print(f"검색 오류 : {e}")

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

                         
class QuerySchema(BaseModel):
    query: str = Field(
        ..., description="여행 지역, 취향 등 조건이 포함된 카페 검색어"
    )
    
class GetCafeInfoTool(BaseTool):
    """네이버 크롤링을 통해 카페 정보 수집"""
    name: str = "Cafe Information Tool"
    description: str = """
    네이버 지도에서 카페를 검색하고 정보를 가져오는 도구입니다.
    검색이 완료되면 카페 목록을 반환하고 작업을 종료합니다.
    한 번의 검색으로 충분한 정보를 제공합니다.
    """
    args_schema: Type[BaseModel] = QuerySchema
    _loop = None
    
    def __init__(self):
        super().__init__()
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
    
    # 리소스 정리        
    def __del__(self):
        if WebDriver._driver:
            WebDriver._driver.quit()
            WebDriver._driver = None        
            
        if self._loop and not self._loop.is_closed():
            self._loop.close()

    async def _collect_reviews(self, cafe_list):
        async with aiohttp.ClientSession() as session:
            tasks = [fetch_review(session, cafe["place_id"]) for cafe in cafe_list]
            return await asyncio.gather(*tasks)
        
    def _run(self, query: str) -> str:
        """동기 실행을 위한 메서드"""
        try:
            cafe_list = cafe_list_crawler(query)
            
            if not cafe_list:
                return json.dumps({
                    "status": "no_results",
                    "message": "검색 결과가 없습니다."
                })

            try:
                reviews = self._loop.run_until_complete(self._collect_reviews(cafe_list))
                
                for cafe, review in zip(cafe_list, reviews):
                    cafe['reviews'] = review.get('reviews', [])

                return json.dumps({
                    "status": "success",
                    "count": len(cafe_list),
                    "cafe_list": cafe_list
                }, ensure_ascii=False)

            except Exception as e:
                print(f"Review collection error: {e}")
                return json.dumps({
                    "status": "error",
                    "message": str(e)
                })

        except Exception as e:
            print(f"Execution error: {e}")
            return json.dumps({
                "status": "error",
                "message": str(e)
            })        
        
    async def _arun(self, query: str) -> str:
        """비동기 실행을 위한 메서드"""
        cafe_list = cafe_list_crawler(query)
        if not cafe_list:
            return json.dumps({
                "status": "no_results",
                "message": "검색 결과가 없습니다."
            })
            
        reviews = await self._collect_reviews([cafe['place_id'] for cafe in cafe_list])


        for cafe in cafe_list:
            cafe_reviews = next((r for r in reviews if r['place_id'] == cafe['place_id']), None)
            if cafe_reviews:
                cafe['reviews'] = cafe_reviews['reviews']
            else:
                cafe['reviews'] = []

        return json.dumps(cafe_list, ensure_ascii=False)

    
