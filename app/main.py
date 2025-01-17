from fastapi import FastAPI
from routers import google_oauth_router
from .routers.kakao_oauth_router import router

from fastapi.middleware.cors import CORSMiddleware
# FastAPI 애플리케이션 생성
app = FastAPI()

app.add_middleware(
    CORSMiddleware, # CORS 미들웨어 등록
    allow_origins=["http://localhost:3000"],  # React 클라이언트 도메인

# Include routers
app.include_router(google_oauth_router.router, prefix="/auth", tags=["Google OAuth"])
app.include_router(router, prefix="/auth", tags=["kakao Login"])

