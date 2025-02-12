from app.dtos.checklist_models import ChecklistCreate, ChecklistResponse
from typing import List
from sqlmodel import Session, select
from fastapi import HTTPException
from app.data_models.data_model import Checklist


# 저장
def save_checklist_item(checklist_items: List[ChecklistCreate], session: Session) -> List[ChecklistResponse]:
    try:
        saved_items = []
        for item in checklist_items:
            checklist_item = Checklist(plan_id=item.plan_id, text=item.text, checked=item.checked)
            session.add(checklist_item)
            session.commit()
            session.refresh(checklist_item)
            
            # ChecklistResponse 모델을 사용하여 응답 데이터 생성
            response_item = ChecklistResponse(
                id=checklist_item.id,
                plan_id=checklist_item.plan_id,
                text=checklist_item.text,
                checked=checklist_item.checked
            )
            saved_items.append(response_item)
        
        return saved_items
    except Exception as e:
        print(f"Error in save_checklist_item repository: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")



#읽기
def read_checklist_item(plan_id: int, session: Session) -> List[ChecklistResponse]:
    try:
        statement = select(Checklist).where(Checklist.plan_id == plan_id)
        results = session.exec(statement).all()
        
        checklist_responses = []
        for item in results:
            checklist_response = ChecklistResponse(
                id=item.id,
                plan_id=item.plan_id,
                text=item.text,
                checked=item.checked
            )
            checklist_responses.append(checklist_response)
        
        return checklist_responses
        
    except Exception as e:
        print(f"Error in read_checklist_item repository: {e}")
        raise HTTPException(status_code=500, detail="데이터베이스 조회 중 오류가 발생했습니다.")


#삭제
def delete_checklist_item(plan_id : int, session: Session):
    try:
        session.exec(Checklist).filter(Checklist.plan_id == plan_id).delete()
        session.commit()
        
        return plan_id
    except Exception as e:
        print(f"Error int delete_checklist_item repository: {e}")


    
    

