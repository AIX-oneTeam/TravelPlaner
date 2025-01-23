from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
from sqlmodel import SQLModel, Session



# 환경 변수 로드
print("--------------------db.py---------------------")

DATABASE_URL = os.getenv("DATABASE_URL")
# DB 설정
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("DB 엔진 생성...")
    engine = create_engine(DATABASE_URL, echo=True)

    print("세션 로컬 생성...")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session) # SQL모델의 세션 사용하도록 설정(exec()메서드 사용위함.)

    app.state.SessionLocal = SessionLocal
    app.state.engine = engine
    
    yield
    print("DB 엔진을 종료하는 중...")
    engine.dispose()


# 동기식 연결
# SQLAlchemy 세션을 생성하고 반환하는 제너레이터
def get_session_sync(request: Request):
    try:
        print("세션을 생성합니다.")
        SessionLocal = request.app.state.SessionLocal
        session = SessionLocal()
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail="데이터 베이스 연결 실패") from e


def drop_table_by_SQLModel():
    print("테이블을 삭제합니다.")
    print("테이블 삭제 완료")

def init_table_by_SQLModel(app: FastAPI): 
    engine = app.state.engine
    with engine.connect() as connection:
        drop_table_by_SQLModel()
        print("테이블을 생성합니다.")
        SQLModel.metadata.create_all(connection)
        print("테이블 생성 완료")



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

