from autogen import ConversableAgent

llm_config = {
    
}


import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
