from fastapi import FastAPI
from app.api.auth.naver import router as naver_router

app = FastAPI()

# 네이버 로그인 라우터 등록
app.include_router(naver_router, prefix="/api/auth")

# 루트 경로 추가
@app.get("/")
def read_root():
    return {"message": "Welcome to the FastAPI Backend!"}
