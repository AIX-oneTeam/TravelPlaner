
from fastapi import Depends
from sqlmodel import Session, select
from app.data_models.data_model import Member
from app.repository.db import get_session_sync


def save_member(member: Member, request) -> int:
    session = get_session_sync(request)
    session.add(member)
    session.commit()

    return member.member_id

def get_member_by_id(member_id: int, request) -> Member:

    session = get_session_sync(request)
    member = session.get(Member, member_id)
    return member if member is not None else None
    

def is_exist_member_by_email(email: str, request) -> bool:

    session = get_session_sync(request)
    print("session type : ", type(session))
    query = select(Member).where(Member.email == email)
    member = session.exec(query).first()
    return True if not member == None else False