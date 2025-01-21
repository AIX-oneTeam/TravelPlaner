import datetime
import os
from dotenv import load_dotenv
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
import jwt

load_dotenv()
JWT_SECRET_KEY = str(os.getenv("JWT_SECRET_KEY", ""))  # 명시적으로 문자열로 변환
JWT_REFRESH_SECRET_KEY = str(os.getenv("JWT_REFRESH_SECRET_KEY", ""))
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

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
   
    #refresh token 생성
def create_refresh_token(payload: dict) -> str:
    current_time = datetime.datetime.utcnow()
    exp_time = current_time + datetime.timedelta(days=30)  # 30일 후 만료
    
    payload.update({
        'iss': 'EasyTravel',  # 발급자
        'sub': str(payload.get('sub', '1')),  # 사용자 식별자
        'exp': int(exp_time.timestamp()),  # 만료 시간
        'iat': int(current_time.timestamp())  # 발급 시간
    })
    
    refresh_token = jwt.encode(payload, JWT_REFRESH_SECRET_KEY, algorithm="HS256")
    return refresh_token

    #jwt 토큰 생성
def create_token_from_oauth(provider: str, auth_info: dict) -> str:
    
    current_time = datetime.datetime.utcnow()  # 현재 시간
    exp_time = current_time + datetime.timedelta(days=1)  # 만료 시간
    
    payload = {
        'iss': 'EasyTravel',  # 발급자
        'sub': str(auth_info.get('id')),  # 사용자 식별자   
        'provider': provider,   # 소셜 로그인 제공자  예) kakao, google
        'exp': int(exp_time.timestamp()),  # 만료 시간
        'iat': int(current_time.timestamp())  # 발급 시간
    }
            
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")
    return token
