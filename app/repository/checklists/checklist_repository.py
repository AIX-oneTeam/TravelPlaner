from app.dtos.checklist_models import ChecklistCreate
from typing import List
from app.data_models.data_model import Checklist
from sqlmodel.ext.asyncio.session import AsyncSession

# 저장
async def save_checklist_item(checklist_items: List[ChecklistCreate], session: AsyncSession) :
    try:
        saved_items = []
        for item in checklist_items :
            checklist_item = Checklist(plan_id=item.plan_id, text=item.text, checked=item.checked)
            await session.add(checklist_item)
            await session.commit()
            await session.refresh(checklist_item)
            saved_items.append(checklist_item)
        return saved_items
    except Exception as e:
        print(f"Error in save_checklist_item repository: {e}")



#읽기
async def read_checklist_item(plan_id: int, session: AsyncSession):
    try:
        got_checklist = await session.exec(Checklist).filter(Checklist.plan_id == plan_id).all()
        return got_checklist
    except Exception as e:
        print(f"Error in read_checklist_item reposotiry: {e}")


#삭제
async def delete_checklist_item(plan_id : int, session: AsyncSession):
    try:
        await session.exec(Checklist).filter(Checklist.plan_id == plan_id).delete()
        await session.commit()
        
        return plan_id
    except Exception as e:
        print(f"Error int delete_checklist_item repository: {e}")


    
    

