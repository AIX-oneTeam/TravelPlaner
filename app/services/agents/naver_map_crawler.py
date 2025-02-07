from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
from datetime import datetime
import asyncio
import aiohttp       
import emoji
from crewai.tools import tool

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
    time.sleep(1)  # (삭제하면 15개만 가져옴)

    # 특정 클래스의 <li> 태그 가져오기
    spots = driver.find_elements(By.CSS_SELECTOR, "li._lazyImgContainer")
    spots_info = []

    for spot in spots:
        if len(spots_info) >= 20:  # 20개까지만 수집
            break
        
        spot_info = {
            "place_id": spot.get_attribute("data-id"),
            "kor_name": spot.get_attribute("data-title"),
            "address": spot.find_element(By.CLASS_NAME, "item_address").text.strip().replace("주소보기\n", ""),
            "image_url": spot.find_element(By.CLASS_NAME, "_itemThumb").find_element(By.TAG_NAME, "img").get_attribute("src"),
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

async def get_cafe_info(query: str) -> dict:
    """
    네이버 지도에서 특정 키워드(query)로 카페 정보를 크롤링하고 리뷰를 가져오는 CrewAI 도구.
    """
    # 시간 측정
    start_time = datetime.now()
    
    # 동기 실행
    cafes_info = cafe_list_crawler(query)
    place_id_list = [cafe["place_id"] for cafe in cafes_info]
    
    # 비동기 실행
    reviews = await fetch_all_reviews(place_id_list)
    
    
    end_time = datetime.now()
    print(f"정보 수집 시간: {(end_time - start_time).total_seconds()}초")  
    
    return {
        "cafe_info" : cafes_info,
        "reviews" : reviews
    }
    
if __name__ == "__main__":
    
    # 크롤링할 네이버 페이지 URL
    query = "강남 조용한 카페" 
    result = asyncio.run(cafe_info(query))
    print(result)

    # 가져온 카페 갯수 20개, 정보 수집시간 11초