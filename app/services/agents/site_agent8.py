from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import os
import asyncio
from dotenv import load_dotenv
import httpx
from serpapi import GoogleSearch
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from aiocache import cached, Cache

# Load environment variables
load_dotenv()

app = FastAPI()

# CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
# LangChain Prompts
# ------------------------------------------------------------------------------

# Place Generation Prompt
place_generation_prompt = PromptTemplate(
    input_variables=["location", "days", "purposes"],
    template="""
You are a travel planner. Suggest exactly {days} * 3 travel destinations for the location "{location}".
The user's purposes are: {purposes}.

Suggest only real and popular tourist attractions or cultural places.

Return the results in the following format:
1일차:
1. 장소명
2. 장소명
3. 장소명
2일차:
1. 장소명
2. 장소명
3. 장소명
""",
)

# Description Generation Prompt
description_prompt = PromptTemplate(
    input_variables=["place_name"],
    template="""
You are a local tour guide. Provide a short description of "{place_name}" in Korean. Include its significance or what makes it unique.

Output format:
설명: <description>
""",
)

# LangChain Chat Model
llm = ChatOpenAI(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o-mini",  # 올바른 모델 이름 사용
    temperature=0,
)

# Use new chain method with `|`
place_generation_chain = place_generation_prompt | llm
description_chain = description_prompt | llm


# ------------------------------------------------------------------------------
# Helper: Search Images with SerpApi (비동기)
# ------------------------------------------------------------------------------
async def search_image_for_place(place_name: str) -> str:
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    if not serpapi_key:
        raise ValueError("SERPAPI_API_KEY is not set in the environment variables.")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://serpapi.com/search",
                params={"q": place_name, "tbm": "isch", "api_key": serpapi_key},
            )
            results = response.json()
            for result in results.get("images_results", []):
                image_url = result.get("original", "")
                if image_url:
                    return image_url
        except Exception as e:
            print(f"Error fetching image for {place_name}: {e}")

    return "https://via.placeholder.com/300"  # Placeholder if no image is found


# ------------------------------------------------------------------------------
# Caching with aiocache
# ------------------------------------------------------------------------------
@cached(ttl=86400, cache=Cache.MEMORY)  # 1일 동안 캐시
async def get_image_url(place: str) -> str:
    return await search_image_for_place(place)


@cached(ttl=86400, cache=Cache.MEMORY)
async def get_place_description(place: str) -> str:
    description_result = await asyncio.to_thread(
        description_chain.invoke, {"place_name": place}
    )
    if hasattr(description_result, "content"):
        return description_result.content.split("설명:")[1].strip()
    return "간단한 설명을 생성할 수 없습니다."


# ------------------------------------------------------------------------------
# Endpoint: /recommendations
# ------------------------------------------------------------------------------
@app.post("/recommendations/", response_model=List[Recommendation])
async def get_recommendations(user_input: UserInput):
    try:
        # Step 1: Generate places using LangChain
        purposes_str = ", ".join(user_input.purposes)

        raw_places = await asyncio.to_thread(
            place_generation_chain.invoke,
            {
                "location": user_input.location,
                "days": user_input.days,
                "purposes": purposes_str,
            },
        )

        # Parse places from LangChain output
        if hasattr(raw_places, "content"):
            raw_places = raw_places.content.strip()

        lines = raw_places.split("\n")
        current_day = 0
        day_destinations_map = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.endswith("일차:"):
                current_day += 1
                day_destinations_map[current_day] = []
                continue

            if line.startswith(("1.", "2.", "3.")):
                place_name = line.split(".")[1].strip()
                day_destinations_map[current_day].append(place_name)

        # Step 2: Fetch images and generate descriptions concurrently
        async def generate_recommendation(place, day, order):
            image_url = await get_image_url(place)
            description = await get_place_description(place)
            return Recommendation(
                picture_url=image_url,
                name=place,
                description=description,
                order=order,
                day=day,
            )

        tasks = [
            generate_recommendation(place, day, order)
            for day, places in day_destinations_map.items()
            for order, place in enumerate(places, start=1)
        ]

        detailed_recommendations = await asyncio.gather(*tasks)
        return detailed_recommendations

    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error generating recommendations: {e}"
        )


# ------------------------------------------------------------------------------
# Run the Server
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
