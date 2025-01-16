from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import RedirectResponse
from ..services.kakao_oauth_service import get_login_url, get_access_token

router = APIRouter()

@router.get("/kakao/login")
async def kakao_login():
    """
    카카오 로그인 페이지로 리다이렉트합니다.
    """
    try:
        # 카카오 로그인 URL 생성
        kakao_oauth_url = get_login_url()
        return RedirectResponse(kakao_oauth_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate Kakao login URL: {e}")


@router.get("/kakao/callback")
async def kakao_callback(code: str = Query(...)):
    """
    카카오 인증 코드를 받아 액세스 토큰을 요청하고 리다이렉트합니다.
    :param code: 카카오에서 반환한 인증 코드
    """
    try:
        # 1. 액세스 토큰 요청
        access_token = await get_access_token(code)

        # 2. 리다이렉트 URL 생성
        redirect_url = f"http://localhost:3000/?access_token={access_token}"
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process Kakao callback: {e}")
