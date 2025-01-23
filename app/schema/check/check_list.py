from datetime import datetime
from typing import Dict
from pydantic import BaseModel

class CheckList(BaseModel):
    plan_id: int # 일정 식별자 (식별 관계)
    check_list: Dict[str, bool] # 체크리스트
    memo: str # 메모
    
    created_at: datetime
    updated_at: datetime