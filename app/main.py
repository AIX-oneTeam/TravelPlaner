from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from .router.kakao_router import router

# FastAPI 애플리케이션 생성
app = FastAPI()

# Jinja2 템플릿 디렉토리 설정
templates = Jinja2Templates(directory="templates")

# 라우터 등록
app.include_router(router, prefix="/auth", tags=["kakao Login"])

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """
    루트 페이지에서 카카오 로그인 버튼이 포함된 HTML 제공
    """
    return templates.TemplateResponse("kakao_login.html", {"request": request})
