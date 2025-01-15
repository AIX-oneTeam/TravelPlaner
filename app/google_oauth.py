from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv
import os
import jwt
from test_db import get_db
from models import Member

# .env 파일 로드
load_dotenv()

# 환경 변수에서 값 로드
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# FastAPI 앱 생성
app = FastAPI()

# Google OAuth 2.0 Flow 설정
flow = Flow.from_client_config(
    {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    },
    scopes=['openid','https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile'],
    redirect_uri=GOOGLE_REDIRECT_URI
)

@app.get("/auth/google-login")
async def google_login():

    # 구글 로그인 URL 생성
    authorization_url, state = flow.authorization_url(
            access_type="offline", # 리프레시 토큰을 받기 위함
            include_granted_scopes="true"  # 이미 승인된 범위 재사용
    )
    print(f"Generated authorization URL: {authorization_url}")
    return RedirectResponse(authorization_url)

@app.get("/auth/google-callback")
async def allback(request: Request, db:Session = Depends(get_db)):
    # 구글에서 인증 완료 후 사용자 정보 받기
    flow.fetch_token(authorization_response=str(request.url))
    credentials = flow.credentials
    # print(vars(credentials))  # 객체의 속성을 딕셔너리 형태로 출력
    
    # id_token 디코딩
    decoded_token = jwt.decode(credentials.id_token, options={"verify_signature": False})
    # print(type(decoded_token)) # dict

    # 사용자 정보
    # refresh_token = credentials.refresh_token
    member_name = decoded_token["name"]
    member_email = decoded_token["email"]


    # 데이터베이스에서 사용자 이메일 검색
    existing_user = db.query(Member).filter(Member.email == member_email).first()

    if not existing_user:
        # 사용자가 없으면 추가
        new_member = Member(
            name=member_name,
            email=member_email
        )
        db.add(new_member)
        db.commit()
        db.refresh(new_member)
        
        print(f"새 사용자 추가: {new_member.name} ({new_member.email})")

        return {"message": "New user added", "member": {"name": new_member.name, "email": new_member.email}}

    # 사용자가 이미 있는 경우
    print(f"기존 사용자 로그인: {existing_user.name} ({existing_user.email})")
    return {"message": "User already exists", "user": {"name": existing_user.name, "email": existing_user.email}}
