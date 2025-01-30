from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import os
import re
from dotenv import load_dotenv

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI

# Load environment variables
load_dotenv()

app = FastAPI()

class UserInput(BaseModel):
    location: str
    date: str
    days: int
    age_group: str
    companions: Dict[str, int]
    purposes: List[str]

class Recommendation(BaseModel):
    picture_url: str
    name: str
    description: str
    order: int
    day: int

# ------------------------------------------------------------------------------
# 1) Analyze user input -> 2~3 major themes
# ------------------------------------------------------------------------------
condition_prompt = PromptTemplate(
    input_variables=["location", "days", "age_group", "purposes"],
    template="""
You are a travel planner. Please analyze the following user information and extract 2-3 main travel themes (e.g., nature, culture, relaxation, activities). Respond in Korean only, without extra text.

- Destination: {location}
- Travel duration: {days} days
- Age group: {age_group}
- Travel purposes: {purposes}

Example output (in Korean):
"자연, 문화, 액티비티"
"""
)

condition_chain = LLMChain(
    llm=ChatOpenAI(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-3.5-turbo",
        temperature=0
    ),
    prompt=condition_prompt
)

# ------------------------------------------------------------------------------
# 2) Provide exactly 3 destinations per day, in Korean
# ------------------------------------------------------------------------------
recommendation_prompt = PromptTemplate(
    input_variables=["themes", "location", "days"],
    template="""
You are a professional travel planner. The user wants to visit {location} for {days} days. The main themes are: {themes}.

Please respond in Korean. Provide exactly 3 destinations for each day using the format:

1일차
1. 장소
2. 장소
3. 장소

2일차
1. 장소
2. 장소
3. 장소

(And so on, if more days.)

Notes:
1. Use real, well-known places as much as possible.
2. If unsure, you can say "장소 정보를 찾기 어렵습니다" (meaning "Hard to find info").
3. Do not add extra explanations; only list the places in the format above.
"""
)

recommendation_chain = LLMChain(
    llm=ChatOpenAI(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-3.5-turbo",
        temperature=0
    ),
    prompt=recommendation_prompt
)

# ------------------------------------------------------------------------------
# 3) Provide short details for each destination (in Korean)
# ------------------------------------------------------------------------------
details_prompt = PromptTemplate(
    input_variables=["destination"],
    template="""
You are a local tour guide. Please provide brief info about "{destination}" in Korean. 
If you're not 100% sure it's fictional, assume it is real and give some possible info.

Format (in Korean):
이름: {destination}
설명: 1~2 sentences
이미지 URL: Must start with http or https (real or example link)

If you are 100% certain this place does not exist, just respond with:
존재하지 않는 장소
"""
)

details_chain = LLMChain(
    llm=ChatOpenAI(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-3.5-turbo",
        temperature=0
    ),
    prompt=details_prompt
)

# ------------------------------------------------------------------------------
# Helper: fill_missing_destinations (3개 min)
# ------------------------------------------------------------------------------
def fill_missing_destinations(destinations, required_count=3):
    default_dest = ["미정"]
    missing_count = required_count - len(destinations)
    if missing_count > 0:
        destinations += default_dest * missing_count
        destinations = destinations[:required_count]
    return destinations

# ------------------------------------------------------------------------------
# Main /recommendations endpoint
# ------------------------------------------------------------------------------
@app.post("/recommendations/", response_model=List[Recommendation])
async def get_recommendations(user_input: UserInput):
    try:
        # 1) Extract main themes (in Korean)
        purpose_str = ", ".join(user_input.purposes)
        condition_summary = condition_chain.run({
            "location": user_input.location,
            "days": user_input.days,
            "age_group": user_input.age_group,
            "purposes": purpose_str
        })
        themes = condition_summary.strip()

        # 2) Get daily recommendations (in Korean)
        raw_recommendations = recommendation_chain.run({
            "themes": themes,
            "location": user_input.location,
            "days": user_input.days
        })

        # Parse line by line
        lines = raw_recommendations.split("\n")
        current_day = 0
        day_destinations_map = {}

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # e.g. "1일차"
            m_day = re.match(r"^(\d+)일차$", line_str)
            if m_day:
                current_day = int(m_day.group(1))
                day_destinations_map[current_day] = []
                continue

            # e.g. "1. 화성행궁"
            m_place = re.match(r"^(\d+)\.\s*(.*)$", line_str)
            if m_place:
                place_name = m_place.group(2).strip()
                if current_day not in day_destinations_map:
                    day_destinations_map[current_day] = []
                day_destinations_map[current_day].append(place_name)
                continue

        # Now we have day_destinations_map with days => list of places
        # 3) For each place, call details_chain
        detailed_recommendations: List[Recommendation] = []

        for day_num in range(1, user_input.days + 1):
            day_list = day_destinations_map.get(day_num, [])
            day_list = fill_missing_destinations(day_list)

            order = 1
            for place in day_list:
                if place == "미정":
                    # fallback
                    detailed_recommendations.append(Recommendation(
                        picture_url="https://via.placeholder.com/300",
                        name="미정",
                        description="정보를 가져오는 데 실패했습니다.",
                        order=order,
                        day=day_num
                    ))
                else:
                    try:
                        detail_text = details_chain.run({"destination": place})
                    except Exception:
                        # fallback text
                        detail_text = (
                            f"이름: {place}\n"
                            "설명: 정보를 가져오는 데 실패했습니다.\n"
                            "이미지 URL: https://via.placeholder.com/300"
                        )

                    if "존재하지 않는 장소" in detail_text:
                        # The chain said it's fictional
                        detailed_recommendations.append(Recommendation(
                            picture_url="https://via.placeholder.com/300",
                            name=place,
                            description="존재하지 않는 장소로 확인되었습니다.",
                            order=order,
                            day=day_num
                        ))
                    else:
                        # Parse lines
                        lines_detail = detail_text.split("\n")
                        name_line = next((l for l in lines_detail if l.startswith("이름:")), None)
                        desc_line = next((l for l in lines_detail if l.startswith("설명:")), None)
                        url_line = next((l for l in lines_detail if l.startswith("이미지 URL:")), None)

                        name_val = place
                        desc_val = "정보 없음"
                        url_val = "https://via.placeholder.com/300"

                        if name_line:
                            name_val = name_line.replace("이름:", "").strip()
                        if desc_line:
                            desc_val = desc_line.replace("설명:", "").strip()
                        if url_line:
                            url_val = url_line.replace("이미지 URL:", "").strip()

                        detailed_recommendations.append(Recommendation(
                            picture_url=url_val,
                            name=name_val,
                            description=desc_val,
                            order=order,
                            day=day_num
                        ))
                order += 1

        return detailed_recommendations

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")


@app.get("/test-recommendations/")
async def test_recommendations():
    return [
        {
            "day": 1,
            "places": [
                {
                    "name": "Test Place 1",
                    "description": "A sample description.",
                    "image_url": "https://example.com/image1.jpg",
                    "order": 1
                },
                {
                    "name": "Test Place 2",
                    "description": "Another sample description.",
                    "image_url": "https://example.com/image2.jpg",
                    "order": 2
                }
            ]
        }
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
