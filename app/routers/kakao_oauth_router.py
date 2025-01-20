from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import RedirectResponse
from app.services.kakao_oauth_service import get_login_url, handle_kakao_callback

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
    카카오 인증 코드를 받아 사용자 정보를 처리합니다.
    :param code: 카카오에서 반환한 인증 코드
    """
    try:
        # 카카오 콜백 처리
        user_info = await handle_kakao_callback(code)
        return {"message": "User info fetched successfully", "user_info": user_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process Kakao callback: {e}")
