from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# DATABASE_URL 설정
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다.")

# MySQL 엔진 생성
engine = create_engine(DATABASE_URL)

# 세션 및 Base 정의
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 데이터베이스 세션 관리 함수
def get_db():
    """
    데이터베이스 세션 관리 함수.
    요청마다 독립적인 세션을 생성하여 관리합니다.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
