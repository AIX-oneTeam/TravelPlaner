import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"..", "..", "..")))

from fastapi import Depends, HTTPException
from sqlmodel import Session
from app.repository.db import get_session_sync
from app.data_models.spot import Spot
from datetime import datetime

def save_spot(spot: Spot, session: Session = Depends(get_session_sync)):
    try:
        session.add(spot)
        session.commit()
        session.refresh(spot)
        print(f"saved spot: {spot}")
    except HTTPException as e:
        print(f"Error: {e.detail}")
        
# 샘플 Spot 데이터
spot_data = Spot(
    kor_name="Test Spot",
    description="A beautiful spot for testing",
    address="123 Test Street",
    zip="12345",
    url="http://example.com",
    image_url="http://example.com/image.jpg",
    map_url="http://example.com/map",
    spot_category=1,
    phone_number="010-3333-9999",
    business_status=True,
    business_hours="9:00-18:00",
)        
  
        
if __name__ == "__main__":
    save_spot()
        