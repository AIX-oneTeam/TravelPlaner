import os
import uvicorn
from dotenv import load_dotenv
from typing import List, Dict, Optional, Type

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import asyncio
import httpx
import json
import requests

# LangChain 관련 import
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain.schema import SystemMessage
from langchain.agents import initialize_agent, AgentType
from langchain_openai import ChatOpenAI
from langchain.tools import BaseTool

# aiocache 관련 import
from aiocache import cached, SimpleMemoryCache

# -----------------------------------------------------
# 1) 환경 변수 로드
# -----------------------------------------------------
load_dotenv()

# -----------------------------------------------------
# 2) FastAPI 설정
# -----------------------------------------------------
app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------
# 3) Pydantic 모델 정의
# -----------------------------------------------------
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


class PlaceInfo(BaseModel):
    title: str
    address: Optional[str]
    phone: Optional[str]
    rating: Optional[float]
    reviews: Optional[int]
    thumbnail: Optional[str]


class ImageInfo(BaseModel):
    url: str
    tags: Optional[str]


class CombinedResult(BaseModel):
    place_info: PlaceInfo
    images: List[ImageInfo]


# -----------------------------------------------------
# 4) LangChain Prompts 정의
# -----------------------------------------------------
# Place Generation Prompt
place_generation_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="""
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
    ...
    """
        ),
        HumanMessagePromptTemplate.from_template("{input}"),
    ]
)

# Description Generation Prompt
description_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="""
    You are a local tour guide. Provide a short description of "{place_name}" in Korean. Include its significance or what makes it unique.
    
    Output format:
    설명: <description>
    """
        ),
        HumanMessagePromptTemplate.from_template("{input}"),
    ]
)

# -----------------------------------------------------
# 5) LangChain LLM 설정
# -----------------------------------------------------
llm = ChatOpenAI(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4",  # 올바른 모델 이름 사용
    temperature=0,
)

# LangChain Chains 생성
place_generation_chain = place_generation_prompt | llm
description_chain = description_prompt | llm


# -----------------------------------------------------
# 6) SerpApi 및 Pixabay Helper 함수 정의
# -----------------------------------------------------
# SerpApi: Google Maps 엔진으로 장소 정보 가져오기 (동기)
def fetch_place_info_from_serpapi(query: str) -> PlaceInfo:
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    if not serpapi_key:
        raise ValueError("SERPAPI_API_KEY is not set in the environment variables.")

    params = {
        "engine": "google_maps",
        "q": query,
        "hl": "ko",
        "gl": "kr",
        "type": "search",
        "api_key": serpapi_key,
    }
    url = "https://serpapi.com/search"
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    local_results = data.get("local_results", [])
    if not local_results:
        # 로컬 결과가 없으면 기본값 반환
        return PlaceInfo(
            title=query,
            address=None,
            phone=None,
            rating=None,
            reviews=None,
            thumbnail=None,
        )

    first_place = local_results[0]
    return PlaceInfo(
        title=first_place.get("title", ""),
        address=first_place.get("address"),
        phone=first_place.get("phone"),
        rating=first_place.get("rating"),
        reviews=first_place.get("reviews"),
        thumbnail=first_place.get("thumbnail"),
    )


# Pixabay: 이미지 검색 (동기)
def fetch_images_from_pixabay(query: str, per_page: int = 3) -> List[ImageInfo]:
    pixabay_key = os.getenv("PIXABAY_API_KEY")
    if not pixabay_key:
        raise ValueError("PIXABAY_API_KEY is not set in the environment variables.")

    params = {
        "key": pixabay_key,
        "q": query,
        "image_type": "photo",
        "per_page": per_page,
    }
    url = "https://pixabay.com/api/"
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    hits = data.get("hits", [])
    results = []
    for hit in hits:
        results.append(
            ImageInfo(url=hit.get("largeImageURL", ""), tags=hit.get("tags", ""))
        )
    return results


# 비동기: SerpApi 이미지 검색 (옵션)
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


# -----------------------------------------------------
# 7) LangChain Tools 정의 (Pydantic v2 호환)
# -----------------------------------------------------
class PlaceSearchInput(BaseModel):
    query: str


class ImageSearchInput(BaseModel):
    query: str


class PlaceSearchTool(BaseTool):
    name: str = "place_search"  # 타입 어노테이션 추가
    description: str = (
        "Use this tool to search for place information (address, rating, phone, etc.) via SerpApi's Google Maps engine."
    )
    args_schema: Type[BaseModel] = PlaceSearchInput

    def _run(self, query: str) -> str:
        """
        동기 방식 SerpApi 호출
        """
        place_info = fetch_place_info_from_serpapi(query)
        return place_info.json()

    async def _arun(self, query: str) -> str:
        """
        비동기 방식 SerpApi 호출
        """
        loop = asyncio.get_event_loop()
        place_info = await loop.run_in_executor(
            None, fetch_place_info_from_serpapi, query
        )
        return place_info.json()


class ImageSearchTool(BaseTool):
    name: str = "image_search"  # 타입 어노테이션 추가
    description: str = "Use this tool to search images from Pixabay."
    args_schema: Type[BaseModel] = ImageSearchInput

    def _run(self, query: str) -> str:
        """
        동기 방식 Pixabay 호출
        """
        images = fetch_images_from_pixabay(query, per_page=5)
        return json.dumps([image.dict() for image in images])

    async def _arun(self, query: str) -> str:
        """
        비동기 방식 Pixabay 호출
        """
        loop = asyncio.get_event_loop()
        images = await loop.run_in_executor(None, fetch_images_from_pixabay, query, 5)
        return json.dumps([image.dict() for image in images])


# -----------------------------------------------------
# 8) LangChain Agent 생성
# -----------------------------------------------------
# 시스템 프롬프트 (Agent에게 지시)
system_prompt = """\
You are a helpful travel planner. You can use the following tools:

1. place_search: To search for place information (address, rating, phone, etc.) via SerpApi's Google Maps engine.
2. image_search: To search for images from Pixabay.

After gathering the necessary information, provide a JSON response with the following structure:
{
  "place_info": {...},
  "images": [...]
}
Make sure to follow the JSON format strictly, do not include extra keys or text.
"""

# 대화 프롬프트 템플릿
prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=system_prompt),
        HumanMessagePromptTemplate.from_template("{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

# LangChain LLM 설정
agent_llm = ChatOpenAI(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4",  # 또는 "gpt-3.5-turbo-16k"
    temperature=0,
)

# Tools 등록
tools = [PlaceSearchTool(), ImageSearchTool()]

# Agent 생성 (initialize_agent 사용)
agent = initialize_agent(
    tools=tools,
    llm=agent_llm,
    agent=AgentType.OPENAI_FUNCTIONS,
    verbose=True,
    prompt=prompt,
)


# -----------------------------------------------------
# 9) FastAPI 엔드포인트 정의
# -----------------------------------------------------
class UserQuery(BaseModel):
    question: str


@app.post("/agent")
async def ask_agent(user_query: UserQuery):
    """
    엔드포인트 예시:
    curl -X POST -H "Content-Type: application/json" \
         -d '{"question": "부산에서 아이랑 갈만한 박물관 알려줘"}' \
         http://localhost:8000/agent
    """
    try:
        # agent.run는 비동기 함수로 사용 가능
        result = await agent.arun(user_query.question)

        # 결과가 JSON 문자열인지 확인하고 파싱
        if isinstance(result, str):
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                # JSON 파싱 실패 시, 기본 응답
                return {"answer": result}
        elif isinstance(result, dict):
            return result
        else:
            return {"answer": str(result)}
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------------------------------
# 10) 서버 실행
# -----------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
