import httpx
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class KakaoService:
    KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")  # .env에서 REST API 키 가져오기
    KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")  # .env에서 Redirect URI 가져오기

    @staticmethod
    async def get_access_token(code: str) -> str:
        """
        카카오로부터 액세스 토큰을 가져옵니다.
        :param code: 카카오 로그인 인증 코드
        :return: 액세스 토큰 (str)
        """
        token_url = "https://kauth.kakao.com/oauth/token"  # 토큰 요청 URL
        data = {
            "grant_type": "authorization_code",
            "client_id": KakaoService.KAKAO_CLIENT_ID,
            "redirect_uri": KakaoService.KAKAO_REDIRECT_URI,
            "code": code,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(token_url, data=data, headers=headers)
                response.raise_for_status()  # HTTP 에러 발생 시 예외 처리
                token_data = response.json()
                print(f"Token Response: {token_data}")  # 디버깅용 출력
                return token_data.get("access_token")  # 'access_token' 가져오기
        except Exception as e:
            print(f"Error fetching access token: {e}")  # 에러 로그 출력
            raise Exception("Failed to fetch access token from Kakao")

    @staticmethod
    async def get_user_info(access_token: str) -> dict:
        """
        액세스 토큰으로 사용자 정보를 가져옵니다.
        :param access_token: 카카오 로그인 액세스 토큰
        :return: 사용자 정보 (dict)
        """
        userinfo_url = "https://kapi.kakao.com/v2/user/me"  # 사용자 정보 요청 URL
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(userinfo_url, headers=headers)
                response.raise_for_status()  # HTTP 에러 발생 시 예외 처리
                user_info = response.json()
                print(f"User Info Response: {user_info}")  # 디버깅용 출력
                return user_info
        except Exception as e:
            print(f"Error fetching user info: {e}")  # 에러 로그 출력
            raise Exception("Failed to fetch user info from Kakao")

    @staticmethod
    def get_login_url() -> str:
        """
        카카오 로그인 URL 생성
        :return: 카카오 로그인 URL (str)
        """
        return (
            f"https://kauth.kakao.com/oauth/authorize"
            f"?client_id={KakaoService.KAKAO_CLIENT_ID}"
            f"&redirect_uri={KakaoService.KAKAO_REDIRECT_URI}"
            f"&response_type=code"
            f"&scope=profile_nickname,profile_image"
            f"&prompt=login"
        )

    @staticmethod
    async def process_kakao_callback(code: str) -> dict:
        """
        인증 코드로 액세스 토큰을 가져오고, 사용자 정보를 처리합니다.
        :param code: 카카오 인증 코드
        :return: 사용자 정보 (dict)
        """
        try:
            # 1. 액세스 토큰 가져오기
            access_token = await KakaoService.get_access_token(code)
            print(f"Access Token: {access_token}")  # 디버깅용 출력

            # 2. 사용자 정보 가져오기
            user_info = await KakaoService.get_user_info(access_token)
            print(f"User Info: {user_info}")  # 디버깅용 출력

            # 3. 사용자 정보 반환
            return {
                "id": user_info.get("id"),
                "nickname": user_info["kakao_account"]["profile"]["nickname"],
                #"email": user_info["kakao_account"].get("email"),
            }
        except KeyError as e:
            print(f"Missing key in user info: {e}")
            raise Exception("Invalid user info structure from Kakao")
        except Exception as e:
            print(f"Error processing Kakao callback: {e}")
            raise Exception("Failed to process Kakao callback")
