from fastapi import FastAPI
from app.api.auth.naver import router as naver_router

app = FastAPI()

app.include_router(naver_router, prefix="/api/auth")
