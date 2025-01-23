# import os
# import sys
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"..", "..", "..")))
from fastapi import Depends, HTTPException
from sqlmodel import Session
from app.data_models.data_model import Spot

def save_spot(spot: Spot, session: Session):
    try:
        session.add(spot)
        session.commit()
        session.refresh(spot)
    except Exception as e:
        session.rollback()  # 트랜잭션 롤백
        print(f"Error while saving spot: {e}")
        raise  # 예외 다시 던지기
    
# 샘플 Spot 데이터
# {
#   "kor_name": "Test Spot",
#   "description": "A beautiful spot for testing",
#   "address": "123 Test Street",
#   "zip": "12345",
#   "url": "http://example.com",
#   "image_url": "http://example.com/image.jpg",
#   "map_url": "http://example.com/map",
#   "spot_category": 1,
#   "phone_number": "010-3333-9999",
#   "business_status": true,
#   "business_hours": "9:00-18:00"
# }    
  