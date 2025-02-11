from pydantic import BaseModel
from typing import List

# 체크리스트 항목 단일 모델
class ChecklistCreate(BaseModel):
    plan_id: int
    text: str
    checked: int

# 여러 체크리스트 항목을 받을 때 사용
class ChecklistListCreate(BaseModel):
    items: List[ChecklistCreate]

# 클라이언트로 응답할 모델
class ChecklistResponse(BaseModel):
    id : int
    plan_id: int
    text: str
    checked: int

class PlanId(BaseModel):
    plan_id : int

