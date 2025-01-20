import datetime
import os
from dotenv import load_dotenv
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
import jwt
import logging

load_dotenv()
JWT_SECRET_KEY = str(os.getenv("JWT_SECRET_KEY", ""))  # 명시적으로 문자열로 변환
JWT_REFRESH_SECRET_KEY = str(os.getenv("JWT_REFRESH_SECRET_KEY", ""))
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_jwt_token(payload: dict) -> str:
    current_time = datetime.datetime.utcnow()
    exp_time = current_time + datetime.timedelta(days=1)
    
    payload.update({
        'iss': 'EasyTravel',
        'sub': '1',
        'exp': int(exp_time.timestamp()),
        'iat': int(current_time.timestamp())
    })
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")
    return token

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

def create_refresh_token(payload: dict) -> str:
    current_time = datetime.datetime.utcnow()
    exp_time = current_time + datetime.timedelta(days=30)
    
    payload.update({
        'iss': 'EasyTravel',
        'sub': '1',
        'exp': int(exp_time.timestamp()),
        'iat': int(current_time.timestamp())
    })
    
    refresh_token = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")
    return refresh_token

def create_token_from_oauth(provider: str, auth_info: dict) -> str:
    logging.debug("Creating OAuth token")
    
    current_time = datetime.datetime.utcnow()
    exp_time = current_time + datetime.timedelta(days=1)
    
    payload = {
        'iss': 'EasyTravel',
        'sub': str(auth_info.get('id')),
        'provider': provider,
        'exp': int(exp_time.timestamp()),
        'iat': int(current_time.timestamp())
    }
    
    logging.debug(f"Using payload: {payload}")
    
    try:
        if not JWT_SECRET_KEY:
            raise ValueError("JWT_SECRET_KEY is empty")
            
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")
        return token
    except Exception as e:
        logging.error(f"Token creation failed: {e}")
        raise

