from app.repository.checklists.checklist_repository import save_checklist_item
from app.dtos.checklist_models import ChecklistCreate
from typing import List
from sqlmodel import Session


async def save_checklist(checklist_items: List[ChecklistCreate], session: Session):
    try:
        saved_checklist_items = save_checklist_item(checklist_items, session)
        return saved_checklist_items
    except Exception as e:
        print(f"Error in save_checklist service: {e}")
        raise Exception("Error saving checklist items")