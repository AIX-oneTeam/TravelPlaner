import datetime
import os
from dotenv import load_dotenv
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
import jwt
import base64
import json

# 환경 변수 로드
load_dotenv()
JWT_SECRET_KEY = str(os.getenv("JWT_SECRET_KEY", ""))
JWT_REFRESH_SECRET_KEY = str(os.getenv("JWT_REFRESH_SECRET_KEY", ""))
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def base64_encode(data: dict) -> str:
    """딕셔너리를 Base64로 인코딩"""
    json_string = json.dumps(data)  # JSON 형식 문자열로 변환
    encoded_data = base64.urlsafe_b64encode(json_string.encode("utf-8")).decode("utf-8")
    return encoded_data


def base64_decode(encoded_data: str) -> dict:
    """Base64로 인코딩된 데이터를 디코딩"""
    decoded_bytes = base64.urlsafe_b64decode(encoded_data.encode("utf-8"))
    return json.loads(decoded_bytes.decode("utf-8"))


def verify_jwt_token(token: str = Depends(oauth2_scheme)) -> dict:
    """
    JWT 검증
    """
    try:
        # JWT 디코딩
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        # Base64 디코딩된 Payload 반환
        return base64_decode(payload["data"])
    except jwt.ExpiredSignatureError:
        raise jwt.ExpiredSignatureError("토큰이 만료되었습니다.")
    except jwt.InvalidTokenError:
        raise jwt.InvalidTokenError("유효하지 않은 토큰입니다.")
    except Exception as e:
        raise e


def create_refresh_token(user_id: str) -> str:
    """
    Refresh Token 생성
    """
    current_time = datetime.datetime.utcnow()
    exp_time = current_time + datetime.timedelta(days=30)  # 30일 후 만료

    # Payload 생성
    payload = {
        'iss': 'EasyTravel',
        'sub': user_id,
        'exp': int(exp_time.timestamp()),
        'iat': int(current_time.timestamp())
    }

    # Payload 전체를 Base64로 인코딩
    encoded_payload = base64_encode(payload)

    # JWT 생성
    refresh_token = jwt.encode({"data": encoded_payload}, JWT_REFRESH_SECRET_KEY, algorithm="HS256")
    return refresh_token


def create_token_from_oauth(provider: str, auth_info: dict) -> str:
    """
    """
    current_time = datetime.datetime.utcnow()
    exp_time = current_time + datetime.timedelta(days=1)  # 1일 후 만료

    # Payload 생성
    payload = {
        'iss': 'EasyTravel',
        'sub': auth_info.get('id'),
        'provider': provider,
        'user_info': auth_info,
        'exp': int(exp_time.timestamp()),
        'iat': int(current_time.timestamp())
    }

    # Payload 전체를 Base64로 인코딩
    encoded_payload = base64_encode(payload)

    # JWT 생성
    token = jwt.encode({"data": encoded_payload}, JWT_SECRET_KEY, algorithm="HS256")
    return token
