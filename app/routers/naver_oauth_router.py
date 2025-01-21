from fastapi import APIRouter, Query, HTTPException, Response, Request
from fastapi.responses import RedirectResponse
from app.services.naver_oauth_service import get_login_url, handle_callback
from app.utils.common import create_jwt

router = APIRouter()

@router.get("/login")
async def naver_login():
    """
    네이버 로그인 URL 생성 후 리다이렉트합니다.
    """
    try:
        login_url = get_login_url()
        return RedirectResponse(login_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate Naver login URL: {e}")

@router.get("/callback")
async def naver_callback(response: Response, code: str = Query(...), state: str = Query(...)):

    """
    네이버 인증 콜백 처리 및 JWT 쿠키 저장
    """
    try:
        user_info = await handle_callback(code, state)
        # JWT 생성
        token = create_jwt({"id": user_info["id"], "email": user_info["email"]})
        # JWT를 쿠키에 저장
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=True,
            samesite="Lax"
        )
        return {"message": "Login successful", "user": user_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process Naver callback: {e}")

@router.get("/protected")
async def protected_route(request: Request):
    """
    보호된 엔드포인트
    """
    user = request.state.user  # 미들웨어에서 설정된 사용자 정보
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"message": "Access granted", "user": user}
