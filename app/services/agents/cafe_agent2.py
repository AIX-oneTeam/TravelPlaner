from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time

cafe_info = {}
# 크롬 드라이버 설정
options = webdriver.ChromeOptions()
options.add_experimental_option("detach", True)  # 창이 자동으로 닫히지 않게 설정
driver = webdriver.Chrome(options=options)

# 네이버 지도 접속
url = "https://map.naver.com/v5/search"
driver.get(url)

# 검색창 요소 찾기 (WebDriverWait 사용)
search_box = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CLASS_NAME, "input_search"))
)

# 검색어 입력
search_box.send_keys("강릉 오션뷰 카페")

# 검색 실행 (ENTER 키)
search_box.send_keys(Keys.ENTER)


# `searchIframe`으로 전환
try:
    WebDriverWait(driver, 10).until(
        EC.frame_to_be_available_and_switch_to_it((By.ID, "searchIframe"))
    )
except:
    print("searchIframe을 찾을 수 없음")
    driver.quit()
    exit()

# 검색 결과 요소 가져오기 (결과가 여러 개일 수도 있으므로 `find_elements` 사용)
try:
    cafe_list = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, "TYaxT"))
    )
    print(f"{len(cafe_list)}개의 카페를 찾았습니다.")
except:
    print("cafe_list를 찾을 수 없음")
    driver.quit()
    exit()

if cafe_list:
    for i in range(7):
        cafe_name = cafe_list[i].text.strip()
        cafe_info[cafe_name] = {"reviews": [], "images": []}  

        cafe_list[i].click()
        driver.switch_to.default_content()

        WebDriverWait(driver, 10).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, "entryIframe"))
        )
        try:
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
            for idx, review in enumerate(review_list):
                review_text = review.text  # 리뷰 텍스트 가져오기
                if review_text != "더보기":
                    cafe_info[cafe_name]["reviews"].append(review_text) 

            image_list = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//a[@class='place_thumb']/img"))
            )

            # 이미지 10개
            for idx, img in enumerate(image_list):
                img_url = img.get_attribute("src")  # 이미지 URL 가져오기
                cafe_info[cafe_name]["images"].append(img_url) 

            driver.switch_to.default_content()
            WebDriverWait(driver, 10).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, "searchIframe"))
            )
        except:
            print("리뷰 버튼이 없습니다.")

import json
result = json.dumps(cafe_info, ensure_ascii=False, indent=4)
print(result)
