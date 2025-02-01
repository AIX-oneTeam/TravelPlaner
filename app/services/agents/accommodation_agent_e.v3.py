from serpapi import GoogleSearch

user_input_data={
    "region" : "대전",
    "check_in_date" : "2025-03-01",
    "check_out_date": "2025-03-03",
    "adults":"2",
    "children":"0"
}

##지역 전체 숙소 검색하기
accommo_list_params = {
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

search = GoogleSearch(accommo_list_params)
results = search.get_dict()

accommodation_names = []
for property in results['properties']:
    if not property['name'].startswith("#"):
        accommodation_names.append(property['name'])
    
print(accommodation_names)


##주소, 전화번호 가져오기 위해서 상세페이지 검색
for name in accommodation_names:
    accommo_one_params = {
        "engine": "google_hotels",
        "q": name,
        "check_in_date": user_input_data["check_in_date"],
        "check_out_date": user_input_data["check_out_date"],
        "adults": user_input_data["adults"],
        "children": user_input_data["children"],
        "currency": "KRW",
        "gl": "kr",
        "hl": "ko",
        "api_key": "my-key"
    }
    
    search = GoogleSearch(accommo_one_params)
    results = search.get_dict()


accommodation_details = []

for property_info in results['properties']:
    detail = {
        "name": property_info.get('name'),
        "address": property_info.get('address'),
        "phone": property_info.get('phone'),
        "check_in_time": property_info.get('check_in_time'),
        "check_out_time": property_info.get('check_out_time')
    }
    
accommodation_details.append(detail)
print(accommodation_details)