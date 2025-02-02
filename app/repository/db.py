from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Session

# 환경 변수 로드
print("--------------------db.py---------------------")
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session) # SQL모델의 세션 사용하도록 설정(exec()메서드 사용위함.)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting application...")
    
    # 데이터베이스 연결 초기화
    app.state.engine = engine

    try:
        yield  # 애플리케이션 실행 동안 유지
    finally:
        print("Shutting down application...")
        
        # 1. 데이터베이스 연결 정리
        app.state.engine.dispose()
        print("Database connection closed.")
        
# 동기식 연결
# SQLAlchemy 세션을 생성하고 반환하는 제너레이터
def get_session_sync():
    session = SessionLocal()
    try:
        print("세션을 생성합니다.")
        yield session
    except Exception as e:
        print(f"[Error] 세션 생성 중 예외 발생: {e}")
        raise RuntimeError("데이터베이스 연결 실패") from e
    finally:
        print("세션을 종료합니다.")
        session.close()

def init_table_by_SQLModel(): 
    with engine.connect() as connection:
        print("테이블을 삭제합니다.")
        SQLModel.metadata.drop_all(connection)
        print("테이블 삭제 완료")
        print("테이블을 생성합니다.")
        SQLModel.metadata.create_all(connection)
        print("테이블 생성 완료")
        
    # 테이블 초기화 시 행정구역 CSV 데이터 삽입
    try:
        import pandas as pd
        data = pd.read_csv('administrative_division.csv')
        data.to_sql('administrative_division', con=engine, if_exists='append', index=False)
        print(f"총 {len(data)}개의 행 삽입 완료.")
    except Exception as e:
        print(f"CSV 데이터 삽입 실패: {e}")
        
def check_table_exists_by_SQLModel():
    print("---------메타데이터 테이블 목록---------")
    print(SQLModel.metadata.tables)
    print("--------------------------------------")

if __name__ == "__main__":
    print("MySQL 연결 테스트를 시작합니다...")
    try:

        load_dotenv()
        DATABASE_URL = os.getenv("DATABASE_URL")
        engine = create_engine(DATABASE_URL, echo=True)
        # 엔진으로 직접 연결 테스트
        with engine.connect() as connection:
            print("MySQL 연결 성공!")

            print("테이블 목록을 출력합니다.")
            result = connection.execute(text("SHOW TABLES;"))

            for row in result:
                print(row)
    except Exception as e:
        print(f"MySQL 연결 실패: {e}")

