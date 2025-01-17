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
        f"https://kauth.kakao.com/oauth/authorize"  # 카카오 로그인 URL
        f"?client_id={KAKAO_CLIENT_ID}" # REST API 키
        f"&redirect_uri={KAKAO_REDIRECT_URI}" # 리다이렉트 URI
        f"&response_type=code"  # 인증 코드 응답 타입
        f"&prompt=login"    
    )


async def get_access_token(code: str) -> str:
    """
    카카오로부터 액세스 토큰을 가져옵니다.
    :param code: 카카오 로그인 인증 코드
    :return: 액세스 토큰 (str)
    """
    token_url = "https://kauth.kakao.com/oauth/token"   #토큰 요청 URL
    data = {
        "grant_type": "authorization_code", # 인증 코드 타입
        "client_id": KAKAO_CLIENT_ID,   #   REST API 키
        "redirect_uri": KAKAO_REDIRECT_URI, # 리다이렉트 URI
        "code": code,   # 카카오 로그인 인증 코드
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"} # 요청 헤더

    try:
        async with httpx.AsyncClient() as client:   # 비동기 HTTP 클라이언트 생성
            response = await client.post(token_url, data=data, headers=headers) #   POST 요청
            response.raise_for_status()  # HTTP 에러 발생 시 예외 처리
            token_data = response.json()    # JSON 데이터 파싱
            return token_data.get("access_token")   # 액세스 토큰 반환
    except httpx.HTTPStatusError as e:
        raise Exception(f"Failed to fetch access token: {e.response.text}") from e
    except Exception as e:
        raise Exception("An unexpected error occurred while fetching access token") from e
