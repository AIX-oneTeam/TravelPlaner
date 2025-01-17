import datetime
import os
from dotenv import load_dotenv
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
import jwt

load_dotenv()
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

# 엔드포인트가 token인 http요청에서 Auth헤더에 있는 토큰 추출
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# JWT 토큰 발행
def create_jwt_token(payload: dict) -> str:
    payload['iss'] = 'EasyTravel'
    # 추후 DB에서 사용자 ID 가져오게끔 수정해야 함.
    payload['sub'] = '1'
    # 만료 시간
    payload['exp'] = datetime.now() + datetime.timedelta(days=1)
    # 발급 시간
    payload['iat'] = datetime.now()
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")
    return token

# JWT 토큰 검증
def verify_jwt_token(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise jwt.ExpiredSignatureError("토큰이 만료되었습니다.")
    except jwt.InvalidTokenError:
        raise jwt.InvalidTokenError("유효하지 않은 토큰입니다.")
    except Exception as e:
        raise e

