from app.dtos.checklist_models import ChecklistCreate
from typing import List
from sqlmodel import Session
from fastapi import HTTPException
from app.data_models.data_model import Checklist


# 저장
def save_checklist_item(checklist_items: List[ChecklistCreate], session: Session) :
    try:
        saved_items = []
        for item in checklist_items :
            checklist_item = Checklist(plan_id=item.plan_id, text=item.text, checked=item.checked)
            session.add(checklist_item)
            session.commit()
            session.refresh(checklist_item)
            saved_items.append(checklist_item)
        return f"saved checklist - {saved_items}" 
    except Exception as e:
        print(f"Error in save_checklist_item repository: {e}")



#읽기
def read_checklist_item(plan_id: int, session: Session):
    try:
        existing_plan = session.exec(Checklist).filter(Checklist.plan_id == plan_id).first()

        if not existing_plan:
            return f"can not find plan_id - {plan_id}" 

        got_checklist = session.exec(Checklist).filter(Checklist.plan_id == plan_id).all()
        return f"got checklist - {got_checklist}" 
    except Exception as e:
        print(f"Error in read_checklist_item reposotiry: {e}")


#삭제
def delete_checklist_item(plan_id : int, session: Session):
    try:
        existing_plan = session.exec(Checklist).filter(Checklist.plan_id == plan_id).first()
        
        if not existing_plan:
            return f"can not find plan_id - {plan_id}" 
        
        session.exec(Checklist).filter(Checklist.plan_id == plan_id).delete()
        session.commit()
        
        return f"deleted checklist plan_id - {plan_id}"
    except Exception as e:
        print(f"Error int delete_checklist_item repository: {e}")


    
    

