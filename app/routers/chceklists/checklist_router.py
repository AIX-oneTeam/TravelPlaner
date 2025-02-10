from fastapi import APIRouter, HTTPException
from sqlmodel import Session
from app.services.checklists.checklist_service import save_checklist
from app.dtos.checklist_models import ChecklistListCreate, ChecklistResponse
from typing import List

router = APIRouter()

@router.post("", response_model=List[ChecklistResponse])
async def add_checklist(checklist_list: ChecklistListCreate, session: Session):
    try:
        saved_checklist = await save_checklist(checklist_list.items, session)
        return saved_checklist
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving checklist: {e}")

