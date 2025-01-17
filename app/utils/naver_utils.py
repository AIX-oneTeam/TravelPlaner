import httpx
from app.config import settings

NAVER_AUTH_URL = "https://nid.naver.com/oauth2.0/token"
NAVER_PROFILE_URL = "https://openapi.naver.com/v1/nid/me"

# 네이버 액세스 토큰 가져오기
async def get_naver_access_token(code: str, state: str):
    """
    네이버로부터 Access Token을 가져오는 함수
    :param code: 네이버에서 반환된 인증 코드
    :param state: 네이버에서 반환된 상태값 (CSRF 방지용)
    :return: Access Token 데이터
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
        try:
            response = await client.post(NAVER_AUTH_URL, params=params)
            response.raise_for_status()  # HTTP 상태 코드 확인
            print("Access Token Response:", response.json())  # 응답 로그 출력
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Failed to fetch Access Token: {e.response.json()}")  # 실패 시 상세 정보 출력
            raise e
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise e


# 네이버 사용자 프로필 가져오기
async def get_naver_user_profile(access_token: str):
    """
    Access Token을 사용해 네이버 사용자 프로필을 가져오는 함수
    :param access_token: 네이버에서 발급받은 Access Token
    :return: 사용자 프로필 데이터
    """
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(NAVER_PROFILE_URL, headers=headers)
            response.raise_for_status()  # HTTP 상태 코드 확인
            print("User Profile Response:", response.json())  # 응답 로그 출력
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Failed to fetch User Profile: {e.response.json()}")  # 실패 시 상세 정보 출력
            raise e
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise e
