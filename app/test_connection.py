# pip install paramiko
# pip install sshtunnel
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

try:
    with SSHTunnelForwarder(
        (SSH_HOST, 22),
        ssh_username=SSH_USER,
        ssh_password=SSH_PASSWORD,
        remote_bind_address=("127.0.0.1", REMOTE_PORT),
        local_bind_address=("127.0.0.1", LOCAL_PORT),
    ) as tunnel:
        print("SSH Tunnel is active.")

        connection = pymysql.connect(
            host=MYSQL_HOST,
            port=tunnel.local_bind_port,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,  # 연결 시 기본 데이터베이스 선택
        )
        print("Connected to MySQL database!")

        # Step 1: Create a cursor
        with connection.cursor() as cursor:
            # Step 2: Execute an SQL query to list tables
            cursor.execute("SHOW TABLES;")
            print("Tables in the database:")
            for table in cursor.fetchall():
                print(table)

            # Step 3: Query a specific table
            table_name = "your_table_name"
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 5;")
            print(f"Data from {table_name}:")
            for row in cursor.fetchall():
                print(row)

except Exception as e:
    print(f"Error: {e}")
finally:
    if 'connection' in locals() and connection.open:
        connection.close()
        print("MySQL connection closed.")
