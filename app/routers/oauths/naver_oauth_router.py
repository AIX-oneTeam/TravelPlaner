from fastapi import APIRouter, Query, HTTPException, Response, Request
from fastapi.responses import RedirectResponse

from app.data_models.data_model import Member
from app.repository.members.mebmer_repository import is_exist_member_by_email, save_member
from app.services.oauths.naver_oauth_service import get_login_url, handle_callback, refresh_naver_access_token
from app.utils.oauths.jwt_utils import create_jwt_naver



router = APIRouter()

# 저장소(메모리 기반 예제)
REFRESH_TOKENS = {}  # 사용자 ID를 키로 하는 리프레시 토큰 저장소


@router.get("/callback")
async def naver_callback(code: str, state: str, response: Response ):
    """
    네이버 인증 콜백 처리 및 JWT 쿠키 저장
    """
    try:
        user_info, tokens = await handle_callback(code, state)
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        # JWT를 쿠키에 저장
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,  # 브라우저에서 접근 불가능하도록 설정
            secure=False,    # HTTPS를 통해서만 전송되도록 설정 (로컬 테스트 중에는 False로 변경 가능)
            samesite="None", # 쿠키 정책 설정
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=False,
            samesite="None",
        )

        # member정보 DB 저장
        if not is_exist_member_by_email(user_info["email"]):
            # 새 회원이면 DB저장
            save_member(Member(
                name=user_info["nickname"],
                email=user_info["email"],
                picture_url=user_info["profile_url"],
                oauth="naver"
            ))

        return {"content": "네이버 로그인 성공",
                    "nickname": user_info["nickname"],
                    "email":user_info["email"],
                    "profile_url":user_info["profile_url"],
                    "roles":user_info["roles"],}
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

@router.get("/refresh")
async def refresh_token(request: Request, response: Response):
    """
    리프레시 토큰을 사용하여 액세스 토큰 갱신
    """
    try:
        user = request.state.user
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        user_id = user["id"]
        refresh_token = REFRESH_TOKENS.get(user_id)
        if not refresh_token:
            raise HTTPException(status_code=400, detail="Refresh token not found")

        # 리프레시 토큰으로 새로운 액세스 토큰 발급
        new_tokens = await refresh_naver_access_token(refresh_token)
        new_access_token = new_tokens["access_token"]

        # 새 JWT 생성 및 저장
        new_jwt = create_jwt_naver({"id": user["id"], "email": user["email"]})
        response.set_cookie(
            key="access_token",
            value=new_jwt,
            httponly=True,
            secure=True,
            samesite="Lax",
        )
        return {"message": "Token refreshed successfully", "access_token": new_access_token}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh token: {e}")
