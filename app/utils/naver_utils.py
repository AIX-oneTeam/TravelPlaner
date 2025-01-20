import httpx
from app.config import settings

NAVER_TOKEN_URL = "https://nid.naver.com/oauth2.0/token"
NAVER_PROFILE_URL = "https://openapi.naver.com/v1/nid/me"

async def get_naver_access_token(code: str, state: str) -> dict:
    """
    네이버로부터 액세스 토큰을 가져옵니다.
    """
    params = {
        "grant_type": "authorization_code",
        "client_id": settings.NAVER_CLIENT_ID,
        "client_secret": settings.NAVER_CLIENT_SECRET,
        "redirect_uri": settings.NAVER_REDIRECT_URI,
        "code": code,
        "state": state,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(NAVER_TOKEN_URL, params=params)
        response.raise_for_status()
        return response.json()


async def get_naver_user_profile(access_token: str) -> dict:
    """
    네이버 사용자 프로필 정보를 가져옵니다.
    """
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(NAVER_PROFILE_URL, headers=headers)
        response.raise_for_status()
        return response.json()
