import os
import httpx
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")  # REST API 키
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")  # 리다이렉트 URI


def get_login_url() -> str:
    """
    카카오 로그인 URL 생성
    :return: 카카오 로그인 URL (str)
    """
    return (
        f"https://kauth.kakao.com/oauth/authorize"
        f"?client_id={KAKAO_CLIENT_ID}"
        f"&redirect_uri={KAKAO_REDIRECT_URI}"
        f"&response_type=code"
        f"&prompt=login"
    )


async def get_access_token(code: str) -> str:
    """
    카카오로부터 액세스 토큰을 가져옵니다.
    :param code: 카카오 로그인 인증 코드
    :return: 액세스 토큰 (str)
    """
    token_url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": KAKAO_CLIENT_ID,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "code": code,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data, headers=headers)
            response.raise_for_status()  # HTTP 에러 발생 시 예외 처리
            token_data = response.json()
            return token_data.get("access_token")
    except httpx.HTTPStatusError as e:
        raise Exception(f"Failed to fetch access token: {e.response.text}") from e
    except Exception as e:
        raise Exception("An unexpected error occurred while fetching access token") from e
