from sshtunnel import SSHTunnelForwarder
import pymysql
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.exc import OperationalError

# Load environment variables
load_dotenv()

SSH_HOST = os.getenv("SSH_HOST")
SSH_USER = os.getenv("SSH_USER")
SSH_PASSWORD = os.getenv("SSH_PASSWORD")
MYSQL_HOST = "127.0.0.1"
LOCAL_PORT = 3307
REMOTE_PORT = 3306
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

# SQLAlchemy 설정
Base = declarative_base()

# get_mysql_connection_url 함수 - SSH 터널을 통해 MySQL 연결 URL을 생성
def get_mysql_connection_url():
    try:
        with SSHTunnelForwarder(
            (SSH_HOST, 22),
            ssh_username=SSH_USER,
            ssh_password=SSH_PASSWORD,
            remote_bind_address=("127.0.0.1", REMOTE_PORT),
            local_bind_address=("127.0.0.1", LOCAL_PORT),
        ) as tunnel:
            print("SSH Tunnel is active.")
            # MySQL 연결 URL 생성
            connection_url = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@127.0.0.1:{tunnel.local_bind_port}/{MYSQL_DATABASE}"
            return connection_url
    except Exception as e:
        print(f"Error: {e}")
        return None

# 데이터베이스 연결 및 세션 설정
def get_db():
    connection_url = get_mysql_connection_url()
    if not connection_url:
        raise Exception("MySQL 연결 URL을 생성할 수 없습니다.")
    
    try:
        # SQLAlchemy 엔진 생성
        engine = create_engine(connection_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # 세션 생성
        db = SessionLocal()
        yield db
    except OperationalError as e:
        print(f"DB 연결 실패: {e}")
    finally:
        db.close()

# MySQL 연결 테스트
def test_mysql_connection():
    connection_url = get_mysql_connection_url()
    if not connection_url:
        print("MySQL 연결 URL 생성 실패")
        return

    print(f"생성된 연결 URL: {connection_url}")

    try:
        # SQLAlchemy를 사용하여 연결 테스트
        engine = create_engine(connection_url)
        with engine.connect() as connection:
            print("MySQL 연결 성공!")
            # 데이터베이스에서 테이블 목록 확인
            result = connection.execute("SHOW TABLES;")
            print("테이블 목록:")
            for row in result:
                print(row)
    except Exception as e:
        print(f"MySQL 연결 실패: {e}")

# 실행 진입점
if __name__ == "__main__":
    print("MySQL 연결 테스트를 시작합니다...")
    test_mysql_connection()
