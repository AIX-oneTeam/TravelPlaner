from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from ...services.oauth2.google_oauth_service import get_google_authorization_url, handle_google_callback

# 로깅 설정
router = APIRouter()


@router.get("/google/callback")
async def google_callback(request: Request):
    """
    구글 인증 코드를 받아 사용자 정보를 처리합니다.
    """
    request_url = str(request.url)
        
        # 구글 콜백 처리 및 사용자 정보 획득
    user_data = await handle_google_callback(request_url)
    return {"message": "구글 로그인이 성공적으로 처리되었습니다.","user_data": user_data}