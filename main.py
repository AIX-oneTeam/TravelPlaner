<<<<<<< HEAD
from fastapi import FastAPI
from app.config.naver_oauth_config import settings  # settings.py에서 settings 불러오기
from fastapi.middleware.cors import CORSMiddleware
from app.routers.naver_oauth_router import router as naver_router
=======
from fastapi import FastAPI, Request
from app.routers.google_oauth_router import router as google_router
from app.routers.kakao_oauth_router import router as kakao_router
from app.routers.naver_oauth_router import router as naver_router
from fastapi.middleware.cors import CORSMiddleware
from app.utils.common import decode_jwt
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
>>>>>>> 858536c3e2a6f5eca224d509f569fd670f20b995

# FastAPI 애플리케이션 생성
app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Hello, world!"}

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 출처 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT 인증 미들웨어 추가
@app.middleware("http")
async def jwt_auth_middleware(request: Request, call_next):
    """
    JWT 인증 미들웨어
    """
    token = request.cookies.get("access_token")  # 쿠키에서 JWT 가져오기
    if token:
        try:
            user_data = decode_jwt(token)  # JWT 디코딩 및 검증
            request.state.user = user_data  # 사용자 정보를 요청 상태에 저장
        except HTTPException:
            # 토큰이 유효하지 않으면 사용자 정보를 추가하지 않음
            request.state.user = None
    else:
        request.state.user = None  # 쿠키가 없으면 None으로 설정
    response = await call_next(request)
    return response


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """
    HTTPException 처리
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

# 라우터 추가
app.include_router(google_router, prefix="/auth/google", tags=["Google OAuth"])
app.include_router(kakao_router, prefix="/auth/kakao", tags=["Kakao Login"])
app.include_router(naver_router, prefix="/auth/naver", tags=["Naver OAuth"])
