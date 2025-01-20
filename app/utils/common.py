import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException

# Secret Key 및 Algorithm 설정
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def create_jwt(data: dict) -> str:
    """
    JWT 생성
    """
    to_encode = data.copy()
    # UTC 시간을 명시적으로 설정
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
