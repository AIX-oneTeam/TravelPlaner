# from sqlalchemy import create_engine
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.exc import OperationalError
# import os
# from dotenv import load_dotenv

# # 환경 변수 로드
# load_dotenv()

# # DATABASE_URL 설정
# DATABASE_URL = os.getenv("DATABASE_URL")
# if not DATABASE_URL:
#     raise ValueError("DATABASE_URL 환경 변수가 설정되지 않았습니다.")

# # 기본 설정
# engine = None
# SessionLocal = None
# Base = declarative_base()

# try:
#     # DB 엔진 및 세션 생성
#     engine = create_engine(DATABASE_URL, pool_pre_ping=True)  # pool_pre_ping으로 연결 상태 확인
#     SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#     # DB 연결 테스트
#     with engine.connect():
#         print("Database connection successful.")
# except OperationalError:
#     print("Database connection failed. Server will run without DB connection.")
#     engine = None
#     SessionLocal = None

# # 데이터베이스 세션 관리 함수
# def get_db():
#     """
#     데이터베이스 세션 관리 함수.
#     DB 연결이 없을 경우 예외를 발생시킵니다.
#     """
#     if not SessionLocal:
#         raise RuntimeError("Database is not connected.")
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
