from fastapi import APIRouter, Response

router = APIRouter()

@router.get("/logout")
async def logout(response: Response):
    """
    로그아웃 처리: 쿠키 삭제
    """
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
    return {"message": "로그아웃 되었습니다."}
