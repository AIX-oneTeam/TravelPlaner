import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    NAVER_CLIENT_ID: str = os.getenv("NAVER_CLIENT_ID")
    NAVER_CLIENT_SECRET: str = os.getenv("NAVER_CLIENT_SECRET")
    NAVER_REDIRECT_URI: str = os.getenv("NAVER_REDIRECT_URI")

settings = Settings()
