from serpapi import GoogleSearch

#구글 맵 검색
map_params = {
  "engine": "google_maps",
  "q": "대전 호텔",
  "ll": "@36.3504,127.3845,15.1z",
  "type": "search",
  "gl": "kr",
  "hl": "ko",
  "api_key": "my-key",
}

search = GoogleSearch(map_params)
map_results = search.get_dict()
local_results = map_results["local_results"]

#숙소 상세 정보 받기
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
    "region" : "대전",
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
  "api_key": "my-key"
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

