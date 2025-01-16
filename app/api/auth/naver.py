from fastapi import APIRouter
from app.config import settings  # 설정 불러오기

router = APIRouter()

@router.get("/naver/login")
def naver_login():
    naver_auth_url = (
        f"https://nid.naver.com/oauth2.0/authorize"
        f"?response_type=code"
        f"&client_id={settings.NAVER_CLIENT_ID}"
        f"&redirect_uri={settings.NAVER_REDIRECT_URI}"
        f"&state=random_state_string"
    )
    return {"naver_auth_url": naver_auth_url}
