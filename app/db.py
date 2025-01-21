from sshtunnel import SSHTunnelForwarder
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
import os
from dotenv import load_dotenv
import atexit
from sqlalchemy.sql import text

# Load environment variables
load_dotenv()

# 환경 변수 가져오기
SSH_HOST = os.getenv("SSH_HOST")
SSH_USER = os.getenv("SSH_USER")
SSH_PASSWORD = os.getenv("SSH_PASSWORD")
MYSQL_HOST = "127.0.0.1"
LOCAL_PORT = 3307
REMOTE_PORT = 3306
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

# 전역 SSH 터널 설정
ssh_tunnel = SSHTunnelForwarder(
    (SSH_HOST, 22),
    ssh_username=SSH_USER,
    ssh_password=SSH_PASSWORD,
    remote_bind_address=("127.0.0.1", REMOTE_PORT),
    local_bind_address=("127.0.0.1", LOCAL_PORT),
)
ssh_tunnel.start()
print("전역 SSH Tunnel이 시작되었습니다.")

# 애플리케이션 종료 시 터널 닫기
atexit.register(lambda: ssh_tunnel.close())

# SQLAlchemy 설정
Base = declarative_base()
connection_url = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@127.0.0.1:{ssh_tunnel.local_bind_port}/{MYSQL_DATABASE}"
engine = create_engine(connection_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

# MySQL 연결 테스트
def test_mysql_connection():
    try:
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
