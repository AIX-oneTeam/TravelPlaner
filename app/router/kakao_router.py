from fastapi import APIRouter, Query, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from ..services.kakao_service import KakaoService

router = APIRouter()
templates = Jinja2Templates(directory="templates")  # templates 폴더 지정

@router.get("/kakao/login")
async def kakao_login():
    """
    카카오 로그인 페이지로 리다이렉트합니다.
    """
    try:
        kakao_oauth_url = KakaoService.get_login_url()
        print(f"[DEBUG] Redirect URI: {KakaoService.KAKAO_REDIRECT_URI}")
        return RedirectResponse(kakao_oauth_url)
    except Exception as e:
        print(f"[ERROR] Failed to generate Kakao login URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate Kakao login URL")


@router.get("/kakao/callback")
async def kakao_callback(request: Request, code: str = Query(...)):
    """
    카카오 로그인 콜백 처리 후 사용자 정보를 보여줍니다.
    """
    try:
        print(f"[DEBUG] Received code: {code}")

        # 액세스 토큰 요청
        access_token = await KakaoService.get_access_token(code)
        print(f"[DEBUG] Access Token: {access_token}")

        # 사용자 정보 요청
        user_info = await KakaoService.get_user_info(access_token)
        print(f"[DEBUG] User Info: {user_info}")

        # 사용자 정보를 저장하거나 템플릿 렌더링으로 전달
        return templates.TemplateResponse(
            "kakao_user.html",
            {
                "request": request,
                "user_info": {
                    "id": user_info.get("id"),
                    "nickname": user_info["properties"].get("nickname", "닉네임 없음"),
                    "profile_image": user_info["properties"].get("profile_image", "프로필 이미지 없음"),
                    "connected_at": user_info.get("connected_at", "연결 날짜 없음"),
                },
            },
        )

    except KeyError as ke:
        print(f"[ERROR] Missing expected key in response: {ke}")
        return JSONResponse(content={"error": "Missing expected key in Kakao response", "details": str(ke)}, status_code=500)

    except Exception as e:
        print(f"[ERROR] Error during Kakao callback processing: {e}")
        return JSONResponse(content={"error": "Callback processing failed", "details": str(e)}, status_code=400)
