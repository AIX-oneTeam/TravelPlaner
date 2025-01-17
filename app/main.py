from fastapi import FastAPI
from .routers.kakao_oauth_router import router
from fastapi.middleware.cors import CORSMiddleware
# FastAPI 애플리케이션 생성
app = FastAPI()


# 라우터 등록
app.include_router(router, prefix="/auth", tags=["kakao Login"])

app.add_middleware(
    CORSMiddleware, # CORS 미들웨어 등록
    allow_origins=["http://localhost:3000"],  # React 클라이언트 도메인
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
