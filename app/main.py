from fastapi import FastAPI, Request
from .routers.oauth2 import auth_reuter, kakao_oauth_router  # kakao_oauth_router 추가
from fastapi.middleware.cors import CORSMiddleware

# FastAPI 애플리케이션 생성
app = FastAPI()



app.add_middleware(
    CORSMiddleware, # CORS 미들웨어 등록
    allow_origins=["http://localhost:3000"],  # React 클라이언트 도메인
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 카카오 OAuth 라우터 추가
app.include_router(kakao_oauth_router.router, prefix="/auth", tags=["Kakao OAuth"])

