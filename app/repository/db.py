import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError

# 환경 변수 로드
load_dotenv()

# DATABASE_URL을 환경 변수에서 가져오기
DATABASE_URL = os.getenv("DATABASE_URL")
Base = declarative_base()

def get_db():
    # SQLAlchemy 엔진 생성
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    # 데이터베이스 세션 생성
    db = SessionLocal()  
    try:
        yield db  # 세션 객체를 반환하고 대기
    except OperationalError as e:
        print(f"DB 연결 실패: {e}")
    finally:
        db.close()  # 작업이 끝난 후 세션을 닫음

if __name__ == "__main__":
    print("MySQL 연결 테스트를 시작합니다...")
    try:
        # 엔진으로 직접 연결 테스트
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            print("MySQL 연결 성공!")
            result = connection.execute(text("SHOW TABLES;"))
            print("테이블 목록:")
            for row in result:
                print(row)
    except Exception as e:
        print(f"MySQL 연결 실패: {e}")

