from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import os
import re
import asyncio
from dotenv import load_dotenv

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType

# Load environment variables
load_dotenv()

app = FastAPI()

# Models
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
# Prompt Definitions (Optimized)
# ------------------------------------------------------------------------------
# 1. Extract main travel themes
condition_prompt = PromptTemplate(
    input_variables=["location", "days", "age_group", "purposes"],
    template="""
You are a travel planner. Analyze the following user input and extract 2-3 main travel themes (e.g., nature, culture, relaxation, activities). Respond in Korean only.

- Destination: {location}
- Travel duration: {days} days
- Age group: {age_group}
- Travel purposes: {purposes}

Example output:
"자연, 문화, 액티비티"
    """
)

# 2. Recommend destinations
recommendation_prompt = PromptTemplate(
    input_variables=["themes", "location", "days"],
    template="""
You are a professional travel planner. The user wants to visit {location} for {days} days. The main themes are: {themes}.

Provide exactly 3 destinations for each day in Korean. Use the format:

1일차
1. 장소
2. 장소
3. 장소

2일차
1. 장소
2. 장소
3. 장소

Notes:
1. Recommend real, well-known places only.
2. If unsure, you can say "장소 정보를 찾기 어렵습니다".
3. Do not include extra explanations or text.
    """
)

# 3. Provide detailed information for destinations
details_prompt = PromptTemplate(
    input_variables=["destination"],
    template="""
You are a local tour guide. Provide brief information about "{destination}" in Korean. Respond with the following format:

이름: {destination}
설명: 1~2 sentences about the place.
이미지 URL: Must be a valid link (real or example).

If this place is fictional or cannot be verified, respond with:
존재하지 않는 장소
    """
)

# ------------------------------------------------------------------------------
# LangChain Chains
# ------------------------------------------------------------------------------
# LLM Instances
llm = ChatOpenAI(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-3.5-turbo",
    temperature=0
)

# Chains
condition_chain = LLMChain(llm=llm, prompt=condition_prompt)
recommendation_chain = LLMChain(llm=llm, prompt=recommendation_prompt)
details_chain = LLMChain(llm=llm, prompt=details_prompt)

# ------------------------------------------------------------------------------
# LangChain Agent
# ------------------------------------------------------------------------------
# Define Tools
tools = [
    Tool(
        name="Extract Travel Themes",
        func=condition_chain.run,
        description="Extracts travel themes based on user input."
    ),
    Tool(
        name="Recommend Destinations",
        func=recommendation_chain.run,
        description="Recommends destinations based on themes and location."
    ),
    Tool(
        name="Provide Destination Details",
        func=details_chain.run,
        description="Provides detailed information about a specific destination."
    )
]

# Initialize Agent
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# ------------------------------------------------------------------------------
# Helper: Fill Missing Destinations (Min 3 per Day)
# ------------------------------------------------------------------------------
def fill_missing_destinations(destinations, required_count=3):
    default_dest = ["미정"]
    missing_count = required_count - len(destinations)
    if missing_count > 0:
        destinations += default_dest * missing_count
        destinations = destinations[:required_count]
    return destinations

# ------------------------------------------------------------------------------
# Main /recommendations Endpoint
# ------------------------------------------------------------------------------
@app.post("/recommendations/", response_model=List[Recommendation])
async def get_recommendations(user_input: UserInput):
    try:
        # Step 1: Extract main themes
        purpose_str = ", ".join(user_input.purposes)
        condition_summary = await asyncio.to_thread(
            condition_chain.run, {
                "location": user_input.location,
                "days": user_input.days,
                "age_group": user_input.age_group,
                "purposes": purpose_str
            }
        )
        themes = condition_summary.strip()

        # Step 2: Get daily recommendations
        raw_recommendations = await asyncio.to_thread(
            recommendation_chain.run, {
                "themes": themes,
                "location": user_input.location,
                "days": user_input.days
            }
        )

        # Parse recommendations by day
        lines = raw_recommendations.split("\n")
        current_day = 0
        day_destinations_map = {}

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Match "1일차"
            m_day = re.match(r"^(\d+)일차$", line_str)
            if m_day:
                current_day = int(m_day.group(1))
                day_destinations_map[current_day] = []
                continue

            # Match "1. 장소"
            m_place = re.match(r"^(\d+)\.\s*(.*)$", line_str)
            if m_place:
                place_name = m_place.group(2).strip()
                day_destinations_map[current_day].append(place_name)

        # Step 3: Get details for each destination
        detailed_recommendations = []

        async def get_details_for_place(place, day, order):
            if place == "미정":
                return Recommendation(
                    picture_url="https://via.placeholder.com/300",
                    name="미정",
                    description="정보를 가져오는 데 실패했습니다.",
                    order=order,
                    day=day
                )
            try:
                detail_text = await details_chain.arun({"destination": place})
                if "존재하지 않는 장소" in detail_text:
                    return Recommendation(
                        picture_url="https://via.placeholder.com/300",
                        name=place,
                        description="존재하지 않는 장소로 확인되었습니다.",
                        order=order,
                        day=day
                    )
                else:
                    lines_detail = detail_text.split("\n")
                    name = next((l.split(":")[1].strip() for l in lines_detail if l.startswith("이름:")), place)
                    description = next((l.split(":")[1].strip() for l in lines_detail if l.startswith("설명:")), "정보 없음")
                    picture_url = next((l.split(":")[1].strip() for l in lines_detail if l.startswith("이미지 URL:")), "https://via.placeholder.com/300")

                    return Recommendation(
                        picture_url=picture_url,
                        name=name,
                        description=description,
                        order=order,
                        day=day
                    )
            except Exception:
                return Recommendation(
                    picture_url="https://via.placeholder.com/300",
                    name=place,
                    description="정보를 가져오는 데 실패했습니다.",
                    order=order,
                    day=day
                )

        for day, places in day_destinations_map.items():
            places = fill_missing_destinations(places)
            tasks = [get_details_for_place(place, day, order) for order, place in enumerate(places, start=1)]
            detailed_recommendations.extend(await asyncio.gather(*tasks))

        return detailed_recommendations

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")

# ------------------------------------------------------------------------------
# Test Endpoint
# ------------------------------------------------------------------------------
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
