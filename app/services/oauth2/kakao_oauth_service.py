import os
import httpx
from dotenv import load_dotenv
from ...utils.jwt_utils import create_token_from_oauth, create_refresh_token
import logging

# .env 파일 로드
load_dotenv()

# 환경 변수 설정 후에 변수 할당
KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")

# 디버깅 로그 추가
logger.debug(f"KAKAO_CLIENT_ID: {KAKAO_CLIENT_ID}")
logger.debug(f"KAKAO_REDIRECT_URI: {KAKAO_REDIRECT_URI}")


s

async def get_login_url() -> str:
    """
    카카오 로그인 URL 생성
    :return: 카카오 로그인 URL (str)
    """
    # REST API 키와 Redirect URI 확인
    if not KAKAO_CLIENT_ID or not KAKAO_REDIRECT_URI:
        logger.error("Kakao CLIENT_ID or REDIRECT_URI is not configured properly.")
        raise ValueError("Kakao CLIENT_ID or REDIRECT_URI is missing.")
    
    # 카카오 로그인 URL 생성
    url = (
        f"https://kauth.kakao.com/oauth/authorize"
        f"?client_id={KAKAO_CLIENT_ID}"  # REST API 키
        f"&redirect_uri={KAKAO_REDIRECT_URI}"  # Redirect URI
        f"&response_type=code"
        f"&prompt=login"
    )
    logger.info("Kakao login URL generated successfully.")
    logger.debug(f"Generated login URL: {url}")
    return url


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
        logger.info("Fetching user info from Kakao.")
        async with httpx.AsyncClient() as client:
            response = await client.get(user_info_url, headers=headers)
            response.raise_for_status()
            user_info = response.json()
            logger.debug(f"User info received: {user_info}")
            return user_info
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to fetch user info: {e.response.text}")
        raise Exception(f"Failed to fetch user info: {e.response.text}") from e
    except Exception as e:
        logger.error("An unexpected error occurred while fetching user info")
        raise Exception("An unexpected error occurred while fetching user info") from e


async def handle_kakao_callback(code: str) -> dict:
    try:
        logger.info("Starting Kakao callback handling process")
        logger.debug(f"Received code: {code}")

        # 액세스 토큰 받기
        access_token = await get_access_token(code)
        if not access_token:
            logger.error("Access token is None or empty")
            raise ValueError("Failed to get access token")
        logger.debug(f"Access token retrieved successfully: {access_token[:10]}...")

        # 사용자 정보 받기
        user_info = await fetch_user_info(access_token)
        if not user_info:
            logger.error("User info is None or empty")
            raise ValueError("Failed to get user info")
        logger.debug(f"User info type: {type(user_info)}")
        logger.debug(f"User info structure: {user_info.keys() if isinstance(user_info, dict) else 'not a dict'}")

        # JWT 토큰 생성 전 데이터 확인
        try:
            jwt_token = create_token_from_oauth("kakao", user_info)
            logger.debug("JWT token created successfully")
        except Exception as jwt_error:
            logger.error(f"JWT token creation failed: {str(jwt_error)}")
            raise jwt_error

        # Refresh 토큰 생성
        try:
            refresh_token = create_refresh_token(user_info)
            logger.debug("Refresh token created successfully")
        except Exception as refresh_error:
            logger.error(f"Refresh token creation failed: {str(refresh_error)}")
            raise refresh_error

        # 반환할 사용자 정보 구성
        response_data = {
            "jwt_token": jwt_token,
            "refresh_token": refresh_token,
            "user_info": {
                "id": str(user_info.get("id", "")),  # id를 문자열로 변환
                "email": user_info.get("kakao_account", {}).get("email"),
                "nickname": user_info.get("kakao_account", {}).get("profile", {}).get("nickname"),
                "profile_image": user_info.get("kakao_account", {}).get("profile", {}).get("profile_image_url"),
            }
        }
        
        logger.debug("Response data prepared successfully")
        return response_data

    except Exception as e:
        logger.error(f"Kakao callback handling failed: {str(e)}", exc_info=True)
        raise Exception(f"Failed to handle Kakao callback: {str(e)}") from e