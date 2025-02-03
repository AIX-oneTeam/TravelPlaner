from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
from serpapi import GoogleSearch
from geopy.geocoders import Nominatim
import os

# FastAPI 앱 생성
app = FastAPI()

# APIRouter 객체 생성
router = APIRouter()

geo_local = Nominatim(user_agent='South Korea')

# Pydantic 모델 정의 - 프론트에서 보내는 데이터 구조
class SearchRequest(BaseModel):
    startDate: int
    endDate: int
    location: str
    age: int
    companions: int
    concept: str

# geocoding 함수 (위도, 경도 받아오는 함수)
def geocoding(address):
    try:
        geo = geo_local.geocode(address)
        if geo:
            x_y = [geo.latitude, geo.longitude]
            return x_y
        else:
            return [0, 0]
    except Exception as e:
        print(f"Error: {e}")
        return [0, 0]

# POST 요청 처리 - /accommo-test 경로에 대한 라우터
@router.post("/accommo-test")
async def search(search_request: SearchRequest):
    start_date = search_request.startDate
    end_date = search_request.endDate
    location = search_request.location
    age = search_request.age
    companions = search_request.companions
    concept = search_request.concept

    # geocoding을 이용하여 위도, 경도 구하기
    coordinates = geocoding(location)
    ll_value = f"@{coordinates[0]},{coordinates[1]},15.1z"

    # 구글 맵 검색
    map_params = {
        "engine": "google_maps",
        "q": f"{location} 호텔",
        "ll": ll_value,
        "type": "search",
        "gl": "kr",
        "hl": "ko",
        "api_key": "key",  # 실제 API 키로 변경
    }

    search = GoogleSearch(map_params)
    map_results = search.get_dict()
    local_results = map_results["local_results"]

    # 숙소 상세 정보 받기
    accommo_map_list = []
    for result in local_results:
        accommo = {
            "name": result.get("title"),
            "address": result.get("address"),
            "phone": result.get("phone")
        }
        accommo_map_list.append(accommo)

    #숙소 이름 리스트 만들기
    accommo_map_name = []
    for result in accommo_map_list:
        accommo_map_name.append(result.get("name"))
        
    print(accommo_map_name)  

    #구글 호텔 - 예약 가능 호텔 리스트 받기
    user_input_data={
        "region" : f"{location}",
        "check_in_date" : "2025-03-01",
        "check_out_date": "2025-03-03",
        "adults":"2",
        "children":"0"
    }

    hotel_params = {
    "engine": "google_hotels",
    "q": user_input_data["region"],
    "check_in_date": user_input_data["check_in_date"],
    "check_out_date": user_input_data["check_out_date"],
    "adults": user_input_data["adults"],
    "children": user_input_data["children"],
    "currency": "KRW",
    "gl": "kr",
    "hl": "ko",
    "api_key": "key"
    }
    
    search = GoogleSearch(hotel_params)
    hotel_results = search.get_dict()

    accommo_hotel_list = []
    if "properties" in hotel_results:
        for result in hotel_results["properties"]:
            accommo_hotel_list.append(result.get("name"))
    else:
        print("호텔 정보가 없습니다.")

    print(accommo_hotel_list)

    common_names = set(accommo_map_name) & set(accommo_hotel_list)
    print(common_names)

    filtered_accommo_map_list = []
    for accommo in accommo_map_list:
        if accommo["name"] in common_names:
            filtered_accommo_map_list.append(accommo)
        
    print(filtered_accommo_map_list)
    
    return filtered_accommo_map_list