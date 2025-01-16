from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv
import os
import jwt
from test_db import get_db
from models import Member
from fastapi.middleware.cors import CORSMiddleware
import requests
# .env 파일 로드
load_dotenv()

# 환경 변수에서 값 로드
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# FastAPI 앱 생성
app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],  # 허용할 클라이언트 도메인
    allow_credentials=True,  # 쿠키와 같은 인증 정보를 포함할지 여부
    allow_methods=["*"],  # 허용할 HTTP 메서드 (예: GET, POST 등)
    allow_headers=["*"],  # 허용할 HTTP 헤더
)

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
    # 반환된 scope가 다르면 오류가 나서 추가 정보를 선택할 수 없고, 아예 다 넣거나 빼야함
    scopes=['openid', # 고유ID(sub), jwt 토큰 반환
            'https://www.googleapis.com/auth/userinfo.email', # 이메일
            'https://www.googleapis.com/auth/userinfo.profile', # 이름, 사진
            # 'https://www.googleapis.com/auth/user.gender.read',
            # 'https://www.googleapis.com/auth/user.birthday.read' 
            ],
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
async def google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        # Google에서 인증 완료 후 사용자 정보 받기
        flow.fetch_token(authorization_response=str(request.url))
        credentials = flow.credentials
        

        # 필수 데이터 처리 (이메일, 이름)
        decoded_token = jwt.decode(credentials.id_token, options={"verify_signature": False})
        family_name = decoded_token.get("family_name")
        given_name = decoded_token.get("given_name")
        name = family_name + given_name
        email = decoded_token.get("email")
        picture = decoded_token.get("picture",None)
        # refresh_token = credentials.refresh_token
        # email_verified = decoded_token.get("email_verified", False)

        access_token = credentials.token
        
        # Access Token을 사용하여 People API 호출
        response = requests.get(
            "https://people.googleapis.com/v1/people/me",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"personFields": "nicknames"}  # nicknames 필드 요청
        )

        if response.status_code == 200:
            user_info = response.json()
            nickname = user_info.get("nicknames", [{}])[0].get("value", None)
            # gender = user_info['genders'][0]['value']
            # birthday_year = user_info['birthdays'][0]['date']['year']
            # birthday_month = user_info['birthdays'][0]['date']['month']
            # birthday_day = user_info['birthdays'][0]['date']['day']
        else:
            print(f"Failed to fetch nickname: {response.status_code} - {response.text}")
            
        existing_user = db.query(Member).filter(Member.email == email).first()

        if not existing_user:
            # 사용자가 없으면 추가
            new_member = Member(
                name=name,
                email=email,
            )
            db.add(new_member)
            db.commit()
            db.refresh(new_member)
            
            print(f"새 사용자 추가: {new_member.name} ({new_member.email})")

            return {"message": "New user added", "member": {"name": new_member.name, "email": new_member.email}}
        
        else:
            print(f"기존 사용자 로그인: {existing_user.name} ({existing_user.email})")

       # 데이터 로깅
        print(f"Email: {email}, Name: {name}, picture: {picture},nickname: {nickname}")

        return RedirectResponse("http://127.0.0.1:3000/")

    except Exception as e:
        print(f"Google OAuth 콜백 처리 중 오류 발생: {e}")
        return {"error": "Google OAuth callback failed"}
