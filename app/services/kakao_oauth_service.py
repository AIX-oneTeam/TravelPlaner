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
            response.raise_for_status()
            token_data = response.json()
            return token_data.get("access_token")
    except httpx.HTTPStatusError as e:
        raise Exception(f"Failed to fetch access token: {e.response.text}") from e
    except Exception as e:
        raise Exception("An unexpected error occurred while fetching access token") from e


async def fetch_user_info(access_token: str) -> dict:
    """
    액세스 토큰을 사용해 카카오 사용자 정보를 가져옵니다.
    :param access_token: 카카오 액세스 토큰
    :return: 사용자 정보 (dict)
    """
    user_info_url = "https://kapi.kakao.com/v2/user/me"
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(user_info_url, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise Exception(f"Failed to fetch user info: {e.response.text}") from e
    except Exception as e:
        raise Exception("An unexpected error occurred while fetching user info") from e


async def handle_kakao_callback(code: str) -> dict:
    """
    카카오 콜백 처리: 액세스 토큰 가져오고 사용자 정보 반환.
    :param code: 카카오 로그인 인증 코드
    :return: 사용자 정보 (dict)
    """
    try:
        # 1. 액세스 토큰 가져오기
        access_token = await get_access_token(code)

        # 2. 사용자 정보 가져오기
        user_info = await fetch_user_info(access_token)

        # 3. 필요한 데이터 반환
        return {
            "id": user_info.get("id"),
            "email": user_info.get("kakao_account", {}).get("email"),
            "nickname": user_info.get("kakao_account", {}).get("profile", {}).get("nickname"),
            "profile_image": user_info.get("kakao_account", {}).get("profile", {}).get("profile_image_url"),
        }
    except Exception as e:
        raise Exception(f"Failed to handle Kakao callback: {e}") from e
