
from fastapi import Depends
from sqlmodel import Session
from app.data_models import member
from app.data_models.member import Member
from app.repository.db import get_session_sync


def save_member(member: Member, session: Session = Depends(get_session_sync)) -> int:
    session.add(member)
    session.commit()

    return member.member_id

def get_member_by_id(member_id: int, session: Session = Depends(get_session_sync)) -> Member:
    member = session.get(Member, member_id)
    return member if member is not None else None
    

def is_exist_member_by_email(email: str, session: Session = Depends(get_session_sync)) -> bool:
    member = session.exec(Member).filter(Member.email == email).first()
    return True if not None else False