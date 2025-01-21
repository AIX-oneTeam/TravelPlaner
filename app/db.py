import os
from sshtunnel import SSHTunnelForwarder
import pymysql
from dotenv import load_dotenv
from sqlalchemy import create_engine,text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError

load_dotenv()

IS_LOCAL = os.getenv("IS_LOCAL", "false")

SSH_HOST = os.getenv("SSH_HOST")
SSH_USER = os.getenv("SSH_USER")
SSH_PASSWORD = os.getenv("SSH_PASSWORD")

MYSQL_HOST = "127.0.0.1"
LOCAL_PORT = 3307
REMOTE_PORT = 3306
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

Base = declarative_base()

def get_mysql_connection_url():
    """
    로컬에서는 SSH 터널 없이 바로 localhost:3306 접근
    원격 접근 시 SSH 터널 생성
    """
    if IS_LOCAL=="true":
        # SSH 터널 없이 바로 접속
        # (MySQL이 로컬 PC에 설치되어 있다고 가정)
        return f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@127.0.0.1:3306/{MYSQL_DATABASE}"
    else:
        # SSH 터널을 이용한 접속
        try:
            with SSHTunnelForwarder(
                (SSH_HOST, 22),
                ssh_username=SSH_USER,
                ssh_password=SSH_PASSWORD,
                remote_bind_address=("127.0.0.1", REMOTE_PORT),
                local_bind_address=("127.0.0.1", LOCAL_PORT),
            ) as tunnel:
                print("SSH Tunnel is active.")
                connection_url = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@127.0.0.1:{tunnel.local_bind_port}/{MYSQL_DATABASE}"
                return connection_url
        except Exception as e:
            print(f"Error: {e}")
            return None

def get_db():
    connection_url = get_mysql_connection_url()
    if not connection_url:
        raise Exception("MySQL 연결 URL을 생성할 수 없습니다.")
    
    try:
        engine = create_engine(connection_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        yield db
    except OperationalError as e:
        print(f"DB 연결 실패: {e}")
    finally:
        db.close()

def test_mysql_connection():
    connection_url = get_mysql_connection_url()
    if not connection_url:
        print("MySQL 연결 URL 생성 실패")
        return

    print(f"생성된 연결 URL: {connection_url}")

    try:
        engine = create_engine(connection_url)
        with engine.connect() as connection:
            print("MySQL 연결 성공!")
            result = connection.execute(text("SHOW TABLES;"))
            print("테이블 목록:")
            for row in result:
                print(row)
    except Exception as e:
        print(f"MySQL 연결 실패: {e}")

if __name__ == "__main__":
    print("MySQL 연결 테스트를 시작합니다...")
    test_mysql_connection()
