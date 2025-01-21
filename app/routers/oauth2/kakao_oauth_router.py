import logging
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import RedirectResponse
from ...services.oauth2.kakao_oauth_service import handle_kakao_callback

router = APIRouter()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.get("/kakao/callback")
async def kakao_callback(code: str, response: Response):
    """
    카카오 인증 콜백: 인증 코드를 받아 JWT와 Refresh Token을 쿠키에 저장.
    """
    redirect_url = "http://localhost:3000/auth/login-success"
    response = RedirectResponse(url=redirect_url)
    try:
        # 1. 인증 코드 수신 로그
        logger.info(f"[Kakao Callback] 받은 인증 코드: {code}")

        # 2. 인증 코드 처리 및 사용자 정보 가져오기
        try:
            user_data = await handle_kakao_callback(code)
            logger.info(f"[Kakao Callback] 사용자 정보 처리 성공: {user_data}")
        except Exception as e:
            logger.error(f"[Kakao Callback] 사용자 정보 처리 실패: {e}")
            raise HTTPException(status_code=400, detail=f"카카오 인증 실패: 사용자 정보 처리 중 오류 발생")   
        # 3. JWT 토큰 쿠키 저장
        try:
            logger.info("[Kakao Callback] JWT 토큰 쿠키 저장 시작")
            response.set_cookie(
                key="jwt_token",
                value=user_data["jwt_token"],
                httponly=True,
                secure=False,  # HTTPS 환경이 아니라면 False로 설정
                samesite="Lax",
                max_age=3600
            )
            logger.info("[Kakao Callback] JWT 토큰 쿠키 저장 완료")
        except Exception as e:
            logger.error(f"[Kakao Callback] JWT 토큰 쿠키 저장 실패: {e}")
            raise HTTPException(status_code=500, detail="JWT 토큰 쿠키 저장 중 오류 발생")

        # 4. Refresh Token 쿠키 저장
        try:
            logger.info("[Kakao Callback] Refresh Token 쿠키 저장 시작")
            response.set_cookie(
                key="refresh_token",
                value=user_data["refresh_token"],
                httponly=True,
                secure=False,
                samesite="Lax",
                max_age=30 * 24 * 60 * 60
            )
            logger.info("[Kakao Callback] Refresh Token 쿠키 저장 완료")
        except Exception as e:
            logger.error(f"[Kakao Callback] Refresh Token 쿠키 저장 실패: {e}")
            raise HTTPException(status_code=500, detail="Refresh Token 쿠키 저장 중 오류 발생")
            

        # 5. 프론트엔드로 리다이렉트
        try:
            logger.info("[Kakao Callback] 프론트엔드로 리다이렉트 시작")
            
            logger.info(f"[Kakao Callback] 리다이렉트 URL: {redirect_url}")
            return response
        except Exception as e:
            logger.error(f"[Kakao Callback] 리다이렉트 실패: {e}")
            raise HTTPException(status_code=500, detail="프론트엔드 리다이렉트 중 오류 발생")

    except Exception as e:
        logger.error(f"[Kakao Callback] 예외 발생: {e}")
        raise HTTPException(status_code=400, detail=f"카카오 인증 실패: {str(e)}")

