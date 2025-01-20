from fastapi import APIRouter, HTTPException
from ...utils.jwt_utils import create_token_from_oauth , create_jwt_token
from typing import Dict
router = APIRouter()

@router.post("/token")
async def create_token(provider: str, auth_info: Dict):
    """
    OAuth 제공자의 인증 정보로 JWT 토큰을 생성합니다.
    """
    try:
        print(f"Provider: {provider}")
        print(f"Auth info: {auth_info}")
        
        # JWT 토큰 생성
        token = await create_token_from_oauth(provider, auth_info)
        
        print(f"Generated token: {token}")
        return {"token": token}
        
    except Exception as e:
        print(f"Token creation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))