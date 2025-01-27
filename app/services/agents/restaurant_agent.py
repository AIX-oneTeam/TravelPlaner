import os
from dotenv import load_dotenv
import requests


def get_coordinates(location, google_maps_api_key):
    """
    Gets latitude and longitude for a given location using Google Geocoding API.

    :param location: Location name (e.g., "부산광역시")
    :param google_maps_api_key: Google Maps API key
    :return: Coordinates as a string "@latitude,longitude,14z"
    """
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": location, "key": google_maps_api_key}

    # 디버그용 프린트 제거
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data["results"]:
            location_data = data["results"][0]["geometry"]["location"]
            latitude = location_data["lat"]
            longitude = location_data["lng"]
            formatted_coordinates = f"@{latitude},{longitude},14z"
            # 좌표 값만 확인
            print(f"Extracted coordinates: {formatted_coordinates}")
            return formatted_coordinates
        else:
            raise Exception("No results found for the location.")
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")


def search_restaurants(test_plan, api_key, google_maps_api_key):
    """
    Searches for restaurants using SerpAPI's Google Maps API.

    :param test_plan: Dictionary containing user-provided travel plan data
    :param api_key: SerpAPI API key
    :param google_maps_api_key: Google Maps API key
    :return: List of restaurants with names, addresses, and ratings
    """
    location = test_plan["main_location"]
    coordinates = get_coordinates(
        location, google_maps_api_key
    )  # Get dynamic coordinates

    url = "https://serpapi.com/search"
    params = {
        "engine": "google_maps",  # Specify the Google Maps engine
        "q": f"{location} 맛집",  # Query in Korean
        "ll": coordinates,  # Dynamically generated coordinates
        "hl": "ko",  # Korean language results
        "gl": "kr",  # South Korea region
        "api_key": api_key,  # SerpAPI API key
        "start": 0,  # Pagination start
    }

    all_restaurants = []
    seen_place_ids = set()  # 중복 제거를 위해 place_id 사용

    for start in [0, 20]:  # Fetch two pages of results (20 each)
        params["start"] = start
        # 디버그용 프린트 제거
        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            results = data.get("local_results", [])

            for result in results:
                name = result.get("title", "No name")
                address = result.get("address", "No address")
                rating = result.get("rating", 0)
                reviews = result.get("reviews", 0)
                place_id = result.get("place_id", "")

                # Filter by rating and reviews, and avoid duplicates
                if rating >= 4 and reviews >= 500 and place_id not in seen_place_ids:
                    all_restaurants.append(
                        {
                            "name": name,
                            "address": address,
                            "rating": rating,
                            "reviews": reviews,
                            "place_id": place_id,
                        }
                    )
                    seen_place_ids.add(place_id)
        else:
            raise Exception(f"Error: {response.status_code}, {response.text}")

    return all_restaurants


if __name__ == "__main__":
    # Load the API key from the .env file
    load_dotenv()
    api_key = os.getenv("SERPAPI_API_KEY")
    google_maps_api_key = os.getenv("GOOGLE_MAP_API_KEY")

    # Example user-provided data
    test_plan = {
        "id": 1,
        "name": "부산 여행",
        "member_id": 0,
        "companion_count": 3,
        "main_location": "부산광역시",
        "concepts": ["가족", "맛집"],
        "uses": 0,
        "start_date": "2025-01-26T11:00:00",
        "end_date": "2025-01-27T16:00:00",
    }

    try:
        # Search for restaurants
        restaurants = search_restaurants(test_plan, api_key, google_maps_api_key)

        # 최종 리스트 결과 출력
        for idx, restaurant in enumerate(restaurants, start=1):
            print(
                f"{idx}. {restaurant['name']} - {restaurant['address']} "
                f"(Rating: {restaurant['rating']}, Reviews: {restaurant['reviews']})"
            )
    except Exception as e:
        print(f"An error occurred: {e}")
