
from fastapi import FastAPI, Request
from app.routers.oauth2.google_oauth_router import router as google_router
from app.routers.oauth2.kakao_oauth_router import router as kakao_router
from app.routers.oauth2.naver_oauth_router import router as naver_router
from fastapi.middleware.cors import CORSMiddleware
from app.utils.common import decode_jwt
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException


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
            # 액세스 토큰이 만료되었으면 리프레시 토큰을 사용하여 새 액세스 토큰을 발급
            refresh_token = request.cookies.get("refresh_token")
            if refresh_token:
                new_access_token = await refresh_access_token(refresh_token)
                # 새 액세스 토큰을 쿠키에 저장
                response = await call_next(request)
                response.set_cookie(
                    key="access_token",
                    value=new_access_token,
                    httponly=True,
                    secure=True,
                    samesite="Lax",
                )
                return response
            request.state.user = None
    else:
        request.state.user = None  # 쿠키가 없으면 None으로 설정
    response = await call_next(request)
    return response

# 리프레시 토큰을 사용해 액세스 토큰을 갱신하는 엔드포인트
@app.get("/refresh-token")
async def refresh_token(request: Request):
    """
    리프레시 토큰을 사용하여 새 액세스 토큰을 발급합니다.
    """
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Refresh token not found")

    new_access_token = await refresh_access_token(refresh_token)
    response = {"message": "Token refreshed successfully"}
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=True,
        samesite="Lax",
    )
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
