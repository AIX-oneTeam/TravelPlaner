from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from ...services.oauth2.google_oauth_service import get_google_authorization_url, handle_google_callback
import logging

# 로깅 설정
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/google/login")
async def google_login():
    """구글 로그인 페이지로 리다이렉트합니다."""
    try:
        logger.info("Generating Google login URL")
        authorization_url = await get_google_authorization_url()
        logger.info(f"Redirecting to Google authorization URL")
        return RedirectResponse(authorization_url)
    except Exception as e:
        logger.error(f"Error generating Google login URL: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="구글 로그인 URL 생성에 실패했습니다."
        )

@router.get("/google/callback")
async def google_callback(request: Request):
    """
    구글 인증 코드를 받아 사용자 정보를 처리합니다.
    """
    try:
        logger.info("Processing Google callback")
        request_url = str(request.url)
        
        # 구글 콜백 처리 및 사용자 정보 획득
        user_data = await handle_google_callback(request_url)
        
        logger.info("Google callback processed successfully")
        return {
            "message": "구글 로그인이 성공적으로 처리되었습니다.",
            "data": user_data
        }
    
    except Exception as e:
        logger.error(f"Error processing Google callback: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="구글 로그인 처리 중 오류가 발생했습니다."
        )
