
from contextlib import asynccontextmanager, contextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import HTTPException
from sqlalchemy import create_engine
from sqlmodel import Session
from sqlalchemy.orm import sessionmaker

from app.repository.db import init_table_by_SQLModel, lifespan
from app.routers.members.member_router import router as member_router
from app.routers.spots.spot_router import router as spot_router
from app.routers.plans.plan_router import router as plan_router
from app.routers.plans.plan_spots_router import router as plan_spots_router
from app.routers.oauths.google_oauth_router import router as google_oauth_router
from app.routers.oauths.kakao_oauth_router import router as kakao_oauth_router
from app.routers.oauths.naver_oauth_router import router as naver_oauth_router
from app.utils.oauths.jwt_utils import decode_jwt, refresh_access_token_naver

import os
from dotenv import load_dotenv

load_dotenv()



# FastAPI 애플리케이션 생성
app = FastAPI(lifespan=lifespan)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 모든 출처 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# # JWT 인증 미들웨어 추가
# @app.middleware("http")
# async def jwt_auth_middleware(request: Request, call_next):
#     """
#     JWT 인증 미들웨어
#     """
#     print("JWT 인증 미들웨어")
#     token = request.cookies.get("access_token")  # 쿠키에서 JWT 가져오기
#     if token:
#         try:
#             user_data = decode_jwt(token)  # JWT 디코딩 및 검증
#             request.state.user = user_data  # 사용자 정보를 요청 상태에 저장
#         except HTTPException:
#             # 액세스 토큰이 만료되었으면 리프레시 토큰을 사용하여 새 액세스 토큰을 발급
#             refresh_token = request.cookies.get("refresh_token")
#             if refresh_token:
#                 new_access_token = await refresh_access_token_naver(refresh_token)
#                 # 새 액세스 토큰을 쿠키에 저장
#                 response = await call_next(request)
#                 response.set_cookie(
#                     key="access_token",
#                     value=new_access_token,
#                     httponly=True,
#                     secure=True,
#                     samesite="Lax",
#                 )
#                 return response
#             request.state.user = None
#     else:
#         request.state.user = None  # 쿠키가 없으면 None으로 설정
#     response = await call_next(request)
#     return response

@app.get("/")
async def root():
    return HTMLResponse(
        """
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <title>EasyTravel Server</title>
        </head>
        <body>
            <h1>EasyTravel Server</h1>
            <p>API 서버가 정상적으로 작동 중입니다.</p>
        </body>
        </html>
        """
    
    )


# 리프레시 토큰을 사용해 액세스 토큰을 갱신하는 엔드포인트
@app.get("/refresh-token")
async def refresh_token(request: Request):
    """
    리프레시 토큰을 사용하여 새 액세스 토큰을 발급합니다.
    """
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Refresh token not found")

    new_access_token = await refresh_access_token_naver(refresh_token)
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
app.include_router(google_oauth_router, prefix="/oauths/google", tags=["Google Oauth"])
app.include_router(kakao_oauth_router, prefix="/oauths/kakao", tags=["Kakao Oauth"])
app.include_router(naver_oauth_router, prefix="/oauths/naver", tags=["Naver Oauth"])
app.include_router(member_router, prefix="/members", tags=["members"])
app.include_router(plan_router, prefix="/plans", tags=["plans"])
app.include_router(spot_router, prefix="/spots", tags=["spots"])
app.include_router(plan_spots_router, prefix="/plan_spots", tags=["plan_spots"])

# 데이터베이스 초기화
# init_table_by_SQLModel()