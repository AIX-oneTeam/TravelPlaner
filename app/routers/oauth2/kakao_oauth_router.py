from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import RedirectResponse
from ...services.oauth2.kakao_oauth_service import get_login_url, handle_kakao_callback
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/kakao/login")
async def kakao_login() -> str:
    """
    카카오 로그인 페이지로 리다이렉트합니다.
    """
    try:
        logger.info("Generating Kakao login URL.")
        # 카카오 로그인 URL 생성
        kakao_oauth_url = await get_login_url()
        logger.info(f"Kakao login URL generated: {kakao_oauth_url}")
        return RedirectResponse(kakao_oauth_url)
    except Exception as e:
        logger.error(f"Error generating Kakao login URL: {e}")
        raise HTTPException(status_code=500, detail="카카오 로그인 URL 생성에 실패했습니다. 잠시 후 다시 시도해 주세요.")


@router.get("/kakao/callback")
async def kakao_callback(code: str = Query(...)):
    """
    카카오 인증 코드를 받아 사용자 정보를 처리합니다.
    :param code: 카카오에서 반환한 인증 코드
    """
    try:
        logger.info(f"Received Kakao callback with code: {code}")
        # 카카오 콜백 처리
        user_info = await handle_kakao_callback(code)
        logger.info(f"User info successfully retrieved: {user_info}")
        return {"message": "사용자 정보가 성공적으로 가져왔습니다.", "user_info": user_info}
    except Exception as e:
        logger.error(f"Error processing Kakao callback: {e}")
        raise HTTPException(status_code=500, detail="카카오 콜백 처리에 실패했습니다. 잠시 후 다시 시도해 주세요.")