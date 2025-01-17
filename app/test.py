from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, tool
from langchain.agents.agent_types import AgentType
import requests
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()
# 환경 변수에서 API 키 가져오기
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_SECRET_ID = os.getenv("NAVER_SECRET_ID")
