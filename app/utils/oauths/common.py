import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException

# Secret Key 및 Algorithm 설정
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7  # 리프레시 토큰 유효기간

def create_jwt(data: dict, is_refresh: bool = False) -> str:
    """
    JWT 생성
    - is_refresh: True인 경우 리프레시 토큰 생성
    """
    to_encode = data.copy()
    # 만료 시간 설정 (UTC 기준)
    if is_refresh:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})  # 만료 시간 추가
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token

def decode_jwt(token: str) -> dict:
    """
    JWT 디코딩 및 검증
    """
    try:
        # JWT 디코딩 및 검증
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def refresh_access_token(refresh_token: str) -> str:
    """
    리프레시 토큰으로 새 액세스 토큰 발급
    """
    try:
        # 리프레시 토큰 디코딩
        payload = decode_jwt(refresh_token)
        # 새 액세스 토큰 생성
        new_access_token = create_jwt({"id": payload["id"], "email": payload["email"]})
        return new_access_token
    except HTTPException as e:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
