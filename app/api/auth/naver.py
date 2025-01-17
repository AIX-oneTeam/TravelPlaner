import secrets
from fastapi import APIRouter, HTTPException, Request, Response
from app.utils.naver_utils import get_naver_access_token, get_naver_user_profile
from app.config import settings

router = APIRouter()

@router.get("/naver/login")
async def naver_login(response: Response):
    # 랜덤한 state 값 생성
    state = secrets.token_urlsafe(16)
    
    # 네이버 로그인 URL 생성
    naver_auth_url = (
        f"https://nid.naver.com/oauth2.0/authorize"
        f"?response_type=code"
        f"&client_id={settings.NAVER_CLIENT_ID}"
        f"&redirect_uri={settings.NAVER_REDIRECT_URI}"
        f"&state={state}"
    )
    
    # 생성된 state 값을 쿠키에 저장 (HTTP-Only로 설정)
    response.set_cookie(key="naver_state", value=state, httponly=True)

    # 클라이언트에 네이버 로그인 URL 반환
    return {"naver_auth_url": naver_auth_url, "state": state}


@router.get("/naver/callback")
async def naver_callback(request: Request, code: str = None, state: str = None):
    # 쿠키에서 저장된 state 값 가져오기
    stored_state = request.cookies.get("naver_state")

    # 디버깅 로그 추가
    print(f"Received state (from Naver): {state}")
    print(f"Stored state (from cookie): {stored_state}")

    # state 값 검증
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")
    if not stored_state or state != stored_state:
        raise HTTPException(status_code=400, detail="State mismatch")

    # 네이버에서 받은 인증 코드로 액세스 토큰 요청
    try:
        token_response = await get_naver_access_token(code, state)
        access_token = token_response.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to get access token")
    except Exception as e:
        print(f"Error while fetching access token: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch access token")

    # 네이버 사용자 프로필 가져오기
    try:
        user_profile = await get_naver_user_profile(access_token)
    except Exception as e:
        print(f"Error while fetching user profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user profile")

    # 사용자 정보를 반환 (필요시 추가 처리 가능)
    return {"user_profile": user_profile}

