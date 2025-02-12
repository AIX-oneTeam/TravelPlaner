
from sqlmodel import  select
from app.data_models.data_model import Member
from sqlmodel.ext.asyncio.session import AsyncSession


async def save_member(member: Member, session: AsyncSession) -> int:
    try:
        await session.add(member)
        return member.id
    except Exception as e:
        print("[ memberRepository ] save_member() 에러 : ", e)


async def get_member_by_id(member_id: int, session: AsyncSession) -> Member:
    try:
        member = await session.get(Member, member_id)
        return member if member is not None else None
    except Exception as e:
        print("[ memberRepository ] get_member_by_id() 에러 : ", e)

async def get_memberId_by_email(email: str, session: AsyncSession) -> Member:
    try:
        query = select(Member).where((Member.email == email))
        member = await session.exec(query).first()
        return member.id if member is not None else None
    except Exception as e:
        print("[ memberRepository ] get_memberId_by_email() 에러 : ", e)

async def is_exist_member_by_email(email: str, oauth: str, session: AsyncSession) -> bool:
    try:
        print("session type : ", type(session))
        query = select(Member).where((Member.email == email) & (Member.oauth == oauth))
        member = await session.exec(query).first()
        return True if not member == None else False
    except Exception as e:
        print("[ memberRepository ] is_exist_member_by_email() 에러 : ", e)