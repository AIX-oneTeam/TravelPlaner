import httpx
import os
import dotenv

dotenv.load_dotenv()

NAVER_TOKEN_URL = "https://nid.naver.com/oauth2.0/token"
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

async def refresh_naver_access_token(refresh_token: str) -> dict:
    """
    리프레시 토큰으로 액세스 토큰을 갱신합니다.
    """
    params = {
        "grant_type": "refresh_token",
        "client_id": NAVER_CLIENT_ID,
        "client_secret": NAVER_CLIENT_SECRET,
        "refresh_token": refresh_token,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(NAVER_TOKEN_URL, params=params)
        response.raise_for_status()
        return response.json()  # 갱신된 액세스 토큰과 새로운 리프레시 토큰을 반환
