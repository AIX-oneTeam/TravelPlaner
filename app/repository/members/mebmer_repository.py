
from fastapi import Depends
from sqlmodel import Session, select
from app.data_models.data_model import Member
from app.repository.db import get_session_sync


def save_member(member: Member, request) -> int:

    try:
        engine = request.app.state.engine
        with Session(engine) as session:
            session.add(member)
            session.commit()
            return member.id
    except Exception as e:
        print("[ memberRepository ] save_member() 에러 : ", e)


def get_member_by_id(member_id: int, request) -> Member:
    try:
        engine = request.app.state.engine
        with Session(engine) as session:
            member = session.get(Member, member_id)
            return member if member is not None else None
    except Exception as e:
        print("[ memberRepository ] get_member_by_id() 에러 : ", e)

def is_exist_member_by_email(email: str, oauth: str, request) -> bool:
    try:
        engine = request.app.state.engine
        with Session(engine) as session:
            print("session type : ", type(session))
            query = select(Member).where((Member.email == email) & (Member.oauth == oauth))
            member = session.exec(query).first()
            return True if not member == None else False
    except Exception as e:
        print("[ memberRepository ] is_exist_member_by_email() 에러 : ", e)