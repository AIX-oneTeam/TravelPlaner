import requests
from bs4 import BeautifulSoup
import json
import re
import emoji
    
def extract_place_info(url):
    url = url.replace('blog.naver.com', 'm.blog.naver.com')

    # User-Agent 설정
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
    }
    
    # 네이버 페이지 요청
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch the URL: {response.status_code}")
        return None

    # BeautifulSoup으로 HTML 파싱
    soup = BeautifulSoup(response.text, "html.parser")
     
    # <script> 태그 중 class="se_module_data" 검색
    a_tag = soup.find("a", class_="se-map-info __se_link")
    if not a_tag:
        print("지도 url이 없는 포스팅입니다. 다른 포스팅을 다시 검색하세요")
        return None

    # 본문 추출
    # content = soup.find('div', {'class': 'se-main-container'})
    # if content:
    #     # 텍스트 추출 및 공백 정리
    #     text = ' '.join(content.stripped_strings)
    #     cleaned_text = re.sub(r'\s+', ' ', text).strip()
        
    #     # 불필요한 문자열 제거
    #     unwanted_strings = ['blog.naver.com', 'search.naver.com', 'open.kakao.com']
    #     for unwanted in unwanted_strings:
    #         cleaned_text = cleaned_text.replace(unwanted, '').strip()

    #     # 이모티콘 제거
    #     cleaned_text = emoji.replace_emoji(cleaned_text, replace='')
            
    # print(cleaned_text)

    # JSON 데이터를 파싱
    try:
        # data-module 속성에서 JSON 데이터 추출
        data_module_content = a_tag.get("data-linkdata")
        data = json.loads(data_module_content)
        place_info={}
        place_info["name"] = data.get("name","")
        place_info["address"] = data.get("address","")
        place_info["latitude"] = data.get("latitude","")
        place_info["longitude"] = data.get("longitude","")
        place_info["tel"] = data.get("tel","")        
        place_info["placeId"] = data.get("placeId","")             

        return json.dumps(data, indent=4, ensure_ascii=False)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        return None

if __name__ == "__main__":
    # 크롤링할 네이버 페이지 URL
    url = "https://blog.naver.com/mymy0802/223381392073" 
    extracted_data = extract_place_info(url)
    
    if extracted_data:
        print("Extracted Data:")
        print(extracted_data)
