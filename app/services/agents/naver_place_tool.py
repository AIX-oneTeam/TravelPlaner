
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
from selenium.common.exceptions import TimeoutException

from crewai.tools import tool

def safe_find_element(driver, by, value, timeout=1, attr="text", default="정보 없음"):
    """
    요소를 안전하게 찾고 값이 없을 경우 기본값 반환
    - driver: Selenium WebDriver 객체
    - by: 요소를 찾는 방법 (By.CLASS_NAME, By.ID 등)
    - value: 요소의 식별자 (클래스명, ID 등)
    - timeout: 최대 대기 시간
    - attr: 반환할 속성 ("text" 또는 "src" 등)
    - default: 요소가 없을 때 반환할 기본값
    """
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return element.get_attribute(attr) if attr != "text" else element.text.strip()
    except TimeoutException:
        return default  # 요소가 없을 경우 기본값 반환
    
@tool("naver_place_tool")    
def naver_place_tool(location, pet_friendly=False, parking=True):
    """
    네이버 지도에서 특정 조건(애견 동반 가능, 주차 가능 등)에 맞는 카페 정보를 검색하는 도구.

    1. 사용법:
    - `query` pet_fri(str): 검색할 키워드, 지역+카페 또는 지역명+특징+카페 (예: 인천 오션뷰 카페), 3단어 이내로 검색
    - `endly` (bool): 애견 동반 가능 필터 적용 (기본값: False)
    - `parking` (bool): 주차 가능 필터 적용 (기본값: True)

    2. 반환값:
    - JSON 형식의 카페 정보, 리뷰 및 이미지 리스트.
    """
    query = f"{location} 카페"
    cafe_info ={}
    # 크롬 드라이버 설정
    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)  # 창이 자동으로 닫히지 않게 설정
    driver = webdriver.Chrome(options=options)

    try:
        # 네이버 지도 접속
        url = "https://map.naver.com/v5/search"
        driver.get(url)

        # 검색창 요소 찾기 (WebDriverWait 사용)
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "input_search"))
        )

        # 검색어 입력
        search_box.send_keys(query)

        # 검색 실행 (ENTER 키)
        search_box.send_keys(Keys.ENTER)


        # `searchIframe`으로 전환
        WebDriverWait(driver, 10).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, "searchIframe"))
        )

        # 검색 결과 요소 가져오기 (결과가 여러 개일 수도 있으므로 `find_elements` 사용)
        if pet_friendly==True:
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[text()='애견동반']"))
            ).click()
            time.sleep(1)

        if parking ==True:
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[text()='주차']"))
            ).click()
            time.sleep(1)

        cafe_list = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "TYaxT"))
        )

        if cafe_list:
            print(f"-----{len(cafe_list)} 개의 cafe 정보 수집 중-----")
            for idx,cafe in enumerate(cafe_list):
                cafe_name = cafe.get_attribute("innerText").strip()
                cafe_info[cafe_name] = {"info":{}, "reviews": [], "images": []}  
                print(f"-----{idx+1} 번째 cafe-----")
                cafe.click()
                driver.switch_to.default_content()

                WebDriverWait(driver, 10).until(
                    EC.frame_to_be_available_and_switch_to_it((By.ID, "entryIframe"))
                )
    
                cafe_info[cafe_name]["info"] = {
                    "address": safe_find_element(driver, By.CLASS_NAME, "LDgIH"),
                    "business_time": safe_find_element(driver, By.CLASS_NAME, "U7pYf"),
                    "tel_number": safe_find_element(driver, By.CLASS_NAME, "xlx7Q"),
                    "home_url": safe_find_element(driver, By.CLASS_NAME, "CHmqa"),
                    "img_url": safe_find_element(driver, By.ID, "ibu_1", attr="src"),
                }

                print(f"-----{idx+1} 번째 cafe info 추가-----")

                # 리뷰 버튼 찾고 클릭
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[text()='리뷰']"))
                ).click()

                # 리뷰 나타날때까지 기다렸다가 스크롤
                time.sleep(2)
                driver.execute_script("window.scrollBy(0, window.innerHeight);")

                # 최신순 버튼 찾고 클릭
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[text()='최신순']"))
                ).click()

                # 최신 리뷰 기다렸다가 크롤링
                time.sleep(2)
                review_list = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//div[@class='pui__vn15t2']/a"))
                )

                # 최신 리뷰 10개
                for review in review_list:
                    review_text = review.text  # 리뷰 텍스트 가져오기
                    if review_text != "더보기":
                        cafe_info[cafe_name]["reviews"].append(review_text) 

                image_list = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//a[@class='place_thumb']/img"))
                )

                print(f"-----{idx+1} 번째 cafe review 추가-----")

                # 이미지 10개
                for img in image_list:
                    img_url = img.get_attribute("src")  # 이미지 URL 가져오기
                    cafe_info[cafe_name]["images"].append(img_url) 


                print(f"-----{idx+1} 번째 cafe image 추가-----")

                driver.switch_to.default_content()
                WebDriverWait(driver, 10).until(
                    EC.frame_to_be_available_and_switch_to_it((By.ID, "searchIframe"))
                )


            driver.quit()
            
            print("--------데이터 수집 결과----------")
            result = json.dumps(cafe_info, ensure_ascii=False, indent=4)
            print(result)
            
            return result
    
    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")
        return json.dumps({"error": "크롤링 실패"}, ensure_ascii=False, indent=4)

    finally:
        driver.quit()  # 예외 발생 여부와 관계없이 항상 드라이버 종료    
