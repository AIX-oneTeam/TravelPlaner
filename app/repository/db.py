import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
from sqlmodel import SQLModel

# 환경 변수 로드
load_dotenv()

# DATABASE_URL을 환경 변수에서 가져오기
DATABASE_URL = os.getenv("DATABASE_URL")
Base = declarative_base()
engine = create_engine(DATABASE_URL, echo=True)
# 동기식 연결
# SQLAlchemy 세션을 생성하고 반환하는 제너레이터 함수
def get_session_sync():
    # SQLAlchemy 엔진 생성
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    # 데이터베이스 세션 생성
    session = SessionLocal()  
    try:
        yield session  # 세션 객체를 반환하고 대기
    except OperationalError as e:
        print(f"DB 연결 실패: {e}")
    finally:
        if(session):
            session.close()  # 작업이 끝난 후 세션을 닫음

def drop_table_by_SQLModel():
    print("테이블을 삭제합니다.")
    print("테이블 삭제 완료")

def init_table_by_SQLModel(): 
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
        # 엔진으로 직접 연결 테스트
        with engine.connect() as connection:
            print("MySQL 연결 성공!")

            print("테이블 목록을 출력합니다.")
            result = connection.execute(text("SHOW TABLES;"))

            for row in result:
                print(row)
    except Exception as e:
        print(f"MySQL 연결 실패: {e}")

