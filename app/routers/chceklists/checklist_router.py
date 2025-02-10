from fastapi import APIRouter, HTTPException
from sqlmodel import Session
from app.services.checklists.checklist_service import save_checklist, read_checklist, delete_checklist
from app.dtos.checklist_models import ChecklistListCreate, ChecklistResponse,PlanId
from typing import List

router = APIRouter()

#저장
@router.post("", response_model=List[ChecklistResponse])
async def add_checklist(checklist_list: ChecklistListCreate, session: Session):
    try:
        saved_checklist = await save_checklist(checklist_list.items, session)
        return saved_checklist
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving checklist: {e}")

#읽기    
@router.get("/{plan_id}", PlanId)
async def get_checklist(plan_id:int, session: Session):
    try:
        got_checklist = await read_checklist(plan_id, session)
        return got_checklist
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting checklist: {e}")
    
#삭제
@router.delete("/{plan_id}", PlanId)
async def delete_checklist(plan_id:int, session: Session):
    try: 
        deleted_checklist =  await delete_checklist(plan_id, session)
        return deleted_checklist
    except Exception as e :
        raise HTTPException(status_code=500, detail=f"Error deleting checklist: {e}")

        
    

