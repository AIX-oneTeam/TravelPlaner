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
        return saved_items
    except Exception as e:
        print(f"Error saving checklist item: {e}")
        raise HTTPException(status_code=500, detail="Error saving checklist item")


#조회


#삭제

