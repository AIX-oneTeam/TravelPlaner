from fastapi import APIRouter, Response

from app.data_models.data_model import Member
from app.repository.members.mebmer_repository import is_exist_member_by_email, save_member
from app.services.oauths.google_oauth_service import handle_google_callback

router = APIRouter()


@router.get("/callback")
async def google_callback(code:str, state:str, response: Response):
    """
    구글 인증 코드를 받아 사용자 정보를 처리합니다.
    """

    # 구글 콜백 처리 및 사용자 정보 획득
    user_data = await handle_google_callback(code, state)
    print("---------------------------------------")
    print("user_data", user_data)
    print("---------------------------------------")

    # JWT 토큰 쿠키 저장
    response.set_cookie(
        key="access_token",
        value=user_data["access_token"],
        max_age=3600,
        samesite="None",
        secure=False,
        httponly=True,
    )

    # Refresh Token 쿠키 저장
    response.set_cookie(
        key="refresh_token",
        value=user_data["refresh_token"],
        max_age=30 * 24 * 60 * 60,
        samesite="None",
        secure=False,
        httponly=True
    )

    # member 정보 DB 저장
    if not is_exist_member_by_email(user_data["email"]):
        # 새 회원이면 DB저장
        save_member(Member(
            name=user_data["nickname"],
            email=user_data["email"],
            picture_url=user_data["profile_url"],
            oauth="google"
        ))

    return {"message": "구글 로그인이 성공적으로 처리되었습니다.",
            "email": user_data["email"],
            "nickname": user_data["nickname"],
            "profile_url": user_data["profile_url"],
            "roles": user_data["roles"]}
    