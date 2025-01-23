from app.data_models.member import Member
from app.repository.members.mebmer_repository import is_exist_member_by_email, save_member


def member_join(member: Member):
    email = member.email
    if not is_exist_member_by_email(email):
        # 새 회원이면 DB저장
        return save_member(member)
    else: pass

def token_to_member(token: str, provider: str):
    # 토큰을 이용해 회원정보를 가져옴
    user_info = None
    if provider == "google":
        user_info = 
    elif provider == "kakao":
        user_info = token.kakao_decode()
    elif provider == "naver":
        user_info = jwt_decode(token)

    # return member
    # 토큰이 유효하지 않으면 None을 반환