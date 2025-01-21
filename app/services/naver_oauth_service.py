from app.utils.naver_utils import get_naver_access_token, get_naver_user_profile
import secrets
from app.config import settings
from app.services.refresh_token_service import refresh_naver_access_token  # 리프레시 토큰 갱신 함수 임포트

def get_login_url() -> str:
    """
    네이버 로그인 URL을 생성합니다.
    """
    state = secrets.token_urlsafe(16)  # 고유한 state 값 생성
    return (
        f"https://nid.naver.com/oauth2.0/authorize"
        f"?response_type=code"
        f"&client_id={settings.NAVER_CLIENT_ID}"
        f"&redirect_uri={settings.NAVER_REDIRECT_URI}"
        f"&state={state}"
    )


async def handle_callback(code: str, state: str) -> tuple:
    """
    네이버 콜백 처리 및 사용자 정보 가져오기.
    액세스 토큰과 리프레시 토큰을 반환하고,
    리프레시 토큰으로 액세스 토큰을 갱신할 수도 있습니다.
    """
    # 액세스 토큰 및 리프레시 토큰 가져오기
    token_response = await get_naver_access_token(code, state)
    access_token = token_response.get("access_token")
    refresh_token = token_response.get("refresh_token")

    if not access_token:
        raise ValueError("Access token not found")

    # 사용자 정보 가져오기
    user_profile = await get_naver_user_profile(access_token)

    # 사용자 정보와 토큰 반환
    return (
        {
            "id": user_profile.get("response", {}).get("id"),
            "email": user_profile.get("response", {}).get("email"),
            "name": user_profile.get("response", {}).get("name"),
            "profile_image": user_profile.get("response", {}).get("profile_image"),
        },
        {"access_token": access_token, "refresh_token": refresh_token},
    )

# 리프레시 토큰을 사용하여 액세스 토큰을 갱신하는 함수
async def refresh_access_token_if_needed(refresh_token: str) -> str:
    """
    리프레시 토큰을 사용하여 액세스 토큰을 갱신합니다.
    """
    if not refresh_token:
        raise ValueError("No refresh token found")

    # 리프레시 토큰을 사용하여 새로운 액세스 토큰을 가져옵니다.
    token_response = await refresh_naver_access_token(refresh_token)
    access_token = token_response.get("access_token")
    if not access_token:
        raise ValueError("Failed to get new access token")

    return access_token
