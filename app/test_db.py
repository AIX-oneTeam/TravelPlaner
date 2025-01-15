from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

# 환경 변수에서 URL 가져오기
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# 세션팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# 자동 커밋 안함(명시적 트랜잭션관리해 데이터 일관성 유지)
# 자동 flush 안함 (add 호출마다 db 동기화로 성능저하 방지)

def get_db():
    db = SessionLocal()  # 데이터베이스 세션 생성
    try:
        yield db  # 세션 객체를 반환하고 대기
    finally:
        db.close()  # 작업이 끝난 후 세션을 닫음

Base = declarative_base()  # ORM 모델의 기본 클래스 생성

