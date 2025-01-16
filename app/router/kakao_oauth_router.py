from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import RedirectResponse
from ..services.kakao_oauth_service import Kakao_oauth_Service

router = APIRouter()

@router.get("/kakao/login")
async def kakao_login():
    """
    카카오 로그인 페이지로 리다이렉트합니다.
    """
    try:
        # 카카오 로그인 URL 생성
        kakao_oauth_url = Kakao_oauth_Service.get_login_url()
        return RedirectResponse(kakao_oauth_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate Kakao login URL: {e}")

@router.get("/kakao/callback")
async def kakao_callback(code: str = Query(...)):
    
    #토큰 요청
    access_token = await Kakao_oauth_Service.get_access_token(code)

    #리다이렉트 URL 생성
    redirect_url = f"http://localhost:3000/?access_token={access_token}"
    return RedirectResponse(url=redirect_url)

