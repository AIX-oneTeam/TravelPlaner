import requests
from bs4 import BeautifulSoup
import json

 
def extract_place_info(query):

    url = f"https://m.map.naver.com/search2/search.naver?query={query}"
    print(url)
    # User-Agent 설정
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
    }
    
    # 네이버 페이지 요청
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch the URL: {response.status_code}")
        # return None

    # BeautifulSoup으로 HTML 파싱
    soup = BeautifulSoup(response.text, "html.parser")

    # <script> 태그 중 class="se_module_data" 검색
    cafe_list = soup.find_all("li", class_="_lazyImgContainer")
    if not cafe_list:
        print("검색어를 변경해서 다시 검색해주세요")
        # return None
    print(cafe_list)
    return cafe_list
    # JSON 데이터를 파싱
    # try:
    #     # data-module 속성에서 JSON 데이터 추출
    #     data_module_content = cafe_list.get("data-linkdata")
    #     data = json.loads(data_module_content)
    #     place_info={}
    #     place_info["name"] = data.get("name","")
    #     place_info["address"] = data.get("address","")
    #     place_info["latitude"] = data.get("latitude","")
    #     place_info["longitude"] = data.get("longitude","")
    #     place_info["tel"] = data.get("tel","")        
    #     place_info["placeId"] = data.get("placeId","")             

    #     return json.dumps(data, indent=4, ensure_ascii=False)
    # except json.JSONDecodeError as e:
    #     print(f"Failed to parse JSON: {e}")
    #     return None

if __name__ == "__main__":
    # 크롤링할 네이버 페이지 URL
    
    query = "강남 마들렌" 
    extracted_data = extract_place_info(query)
    
    if extracted_data:
        print("Extracted Data:")
        print(extracted_data)
