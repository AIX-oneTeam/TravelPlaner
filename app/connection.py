from sshtunnel import SSHTunnelForwarder
import pymysql
import os
from dotenv import load_dotenv

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
            
            # MySQL에 연결할 URL 생성
            connection_url = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@127.0.0.1:{tunnel.local_bind_port}/{MYSQL_DATABASE}"
            return connection_url
    except Exception as e:
        print(f"Error: {e}")
        return None
