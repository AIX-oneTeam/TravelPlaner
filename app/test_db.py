from app.services.mysql_service import Base, engine
from app.models.member import Member  # Member 모델 임포트

# 테이블 생성 (삭제 없이 생성만)
print("새 테이블 생성 중...")
Base.metadata.create_all(bind=engine)

print("MySQL 데이터베이스 테이블 생성 완료")
