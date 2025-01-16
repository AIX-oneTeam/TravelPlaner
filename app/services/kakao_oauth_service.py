import httpx
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class Kakao_oauth_Service:
    KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")  # .env에서 REST API 키 가져오기
    KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")  # .env에서 Redirect URI 가져오기

    @staticmethod
    #토큰을 받아오는 함수
    async def get_access_token(code: str) -> str:
        """
        카카오로부터 액세스 토큰을 가져옵니다.
        :param code: 카카오 로그인 인증 코드
        :return: 액세스 토큰 (str)
        """
        token_url = "https://kauth.kakao.com/oauth/token"  # 토큰 요청 URL
        data = {
            "grant_type": "authorization_code",
            "client_id": Kakao_oauth_Service.KAKAO_CLIENT_ID,
            "redirect_uri": Kakao_oauth_Service.KAKAO_REDIRECT_URI,
            "code": code,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(token_url, data=data, headers=headers)
                response.raise_for_status()  # HTTP 에러 발생 시 예외 처리
                token_data = response.json()
                return token_data.get("access_token")  # 'access_token' 가져오기
        except Exception as e:
            print(f"Error fetching access token: {e}")  # 에러 로그 출력
            raise Exception("Failed to fetch access token from Kakao")

    @staticmethod
    #사용자 정보를 가져오는 함수
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
                return user_info
        except Exception as e:
            print(f"Error fetching user info: {e}")  # 에러 로그 출력
            raise Exception("Failed to fetch user info from Kakao")

    @staticmethod   #
    #로그인 URL을 가져오는 함수
    def get_login_url() -> str:
        """
        카카오 로그인 URL 생성
        :return: 카카오 로그인 URL (str)
        """
        return (
            f"https://kauth.kakao.com/oauth/authorize" # 카카오 기본 url
            f"?client_id={Kakao_oauth_Service.KAKAO_CLIENT_ID}"    # REST API 키
            f"&redirect_uri={Kakao_oauth_Service.KAKAO_REDIRECT_URI}" # 리다이렉트 URL
            f"&response_type=code"  #고정값
            f"&prompt=login"    #로그인
        )

    @staticmethod
    #카카오 로그인 콜백 처리 함수
    async def process_kakao_callback(code: str) -> dict:
        """
        인증 코드로 액세스 토큰을 가져오고, 사용자 정보를 처리합니다.
        :param code: 카카오 인증 코드
        :return: 사용자 정보 (dict)
        """
        try:
            # 가져온 토큰 요청
            access_token = await Kakao_oauth_Service.get_access_token(code)
            print(f"Access Token: {access_token}")  # 디버깅용 출력

            # 가져온 사용자 정보 요청
            user_info = await Kakao_oauth_Service.get_user_info(access_token)
            print(f"User Info: {user_info}")  # 디버깅용 출력
            
            # 3. 사용자 정보 반환
            return {
                "id": user_info.get("id"),
                "nickname": user_info["properties"].get("nickname"),
                "email": user_info["kakao_account"].get("email"),
                
            }
        except Exception as e:
            print(f"Error processing Kakao callback: {e}")
            raise Exception("Failed to process Kakao callback")
        
