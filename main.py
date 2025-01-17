from fastapi import FastAPI
from app.config import settings  # settings.py에서 settings 불러오기
from fastapi.middleware.cors import CORSMiddleware
from app.api.auth.naver import router as naver_router

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 프론트엔드 주소
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메소드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

# 네이버 로그인 라우터 등록
app.include_router(naver_router, prefix="/api/auth")

# 루트 경로 추가
@app.get("/")
def read_root():
    return {"message": "Welcome to the FastAPI Backend!"}

# 네이버 설정 값 확인 (옵션)
@app.get("/check-settings")
def check_settings():
    return {
        "NAVER_CLIENT_ID": settings.NAVER_CLIENT_ID,
        "NAVER_CLIENT_SECRET": settings.NAVER_CLIENT_SECRET,
        "NAVER_REDIRECT_URI": settings.NAVER_REDIRECT_URI
    }
