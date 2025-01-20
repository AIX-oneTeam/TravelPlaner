from app.utils.naver_utils import get_naver_access_token, get_naver_user_profile
import secrets
from app.config import settings

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


async def handle_callback(code: str, state: str) -> dict:
    """
    네이버 콜백 처리 및 사용자 정보 가져오기.
    """
    # 액세스 토큰 가져오기
    token_response = await get_naver_access_token(code, state)
    access_token = token_response.get("access_token")
    if not access_token:
        raise ValueError("Access token not found")

    # 사용자 정보 가져오기
    user_profile = await get_naver_user_profile(access_token)
    return {
        "id": user_profile.get("response", {}).get("id"),
        "email": user_profile.get("response", {}).get("email"),
        "name": user_profile.get("response", {}).get("name"),
        "profile_image": user_profile.get("response", {}).get("profile_image"),
    }
