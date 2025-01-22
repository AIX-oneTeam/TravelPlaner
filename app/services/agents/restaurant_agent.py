import os
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI

# Load .env file
load_dotenv()

# API Key Setup
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI
llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=OPENAI_API_KEY)


# Function to request restaurant recommendations from GPT
def generate_restaurant_recommendations(keywords):
    """Generate restaurant recommendations based on user data using GPT."""
    user_data_description = f"""
    You are an expert in Korean cuisine and a recommendation AI. Based on the travel data provided by the user, recommend the most suitable restaurants.

    The user has provided the following travel plan data:
    - Location: {keywords['location']}
    - Travel Dates: {keywords['dates']}
    - Age Group: {keywords['age_group']}
    - Group Composition: Adults {keywords['group']['adults']}, Children {keywords['group']['children']}, Pets {keywords['group']['pets']}
    - Travel Themes: {', '.join(keywords['themes'])}

    Based on this data, recommend restaurants in the {keywords['location']} area.
    Ensure that the recommendations are accurate and realistic. If you cannot find a valid picture URL for a restaurant, return "N/A" for the picture URL.

    The recommendation schedule must follow these rules:
    - For full travel days (22nd to 24th January 2025), recommend three restaurants per day (breakfast, lunch, and dinner).
    - For the last travel day (25th January 2025), recommend two restaurants (breakfast and lunch).

    The recommendation results should be formatted in JSON and include the following information for each restaurant:

    {{
      "day": "<Day: Day 1, Day 2, etc.>",
      "order": "<Visit Order: 1, 2, 3, etc.>",
      "name": "<Restaurant Name>",
      "description": "<Restaurant Description>",
      "address": "<Address>",
      "category": "<Cuisine Category: Korean/Japanese/Western/etc.>",
      "reason": "<Reason for Recommendation: family-friendly, offers children’s menu, pet-friendly, etc.>",
      "picture_url": "<Picture URL or 'N/A'>",
      "place_description": "<Detailed description of the place, including its ambiance, specialty dishes, and suitability for the group.>"
    }}

    The recommendation results must be in Korean and include information about which restaurants to visit on each day and in which order. Ensure the output is clear, concise, and easy for the user to understand.
    """
    try:
        response = llm.predict(user_data_description)
        if isinstance(response, str):
            return response.strip()
        else:
            print("Invalid response type from GPT.")
            return "추천 실패: GPT 응답 오류."
    except Exception as e:
        print(f"GPT 호출 오류: {e}")
        return "추천 실패: GPT 호출 중 문제가 발생했습니다."


# User keyword input
keywords = {
    "location": "부산 해운대",
    "dates": "2025년 1월 22일 ~ 2025년 1월 25일",
    "age_group": "10대 미만",
    "themes": ["가족 여행", "리조트"],
    "group": {"adults": 2, "children": 1, "pets": 1},
}

# Generate recommendation
recommendation = generate_restaurant_recommendations(keywords)

# Output result
print("\n=== 추천 맛집 ===")
print(recommendation)
