# test_db.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .connection import get_mysql_connection_url  # 연결 URL 가져오는 함수 임포트

# .env 파일 로드
load_dotenv()

# test_connection.py에서 생성한 MySQL 연결 URL 가져오기
DATABASE_URL = get_mysql_connection_url()

if not DATABASE_URL:
    raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다.")

# 데이터베이스 연결 설정
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 데이터베이스 세션 관리 함수
def get_db():
    """
    요청마다 독립적인 데이터베이스 세션을 생성하여 관리합니다.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

