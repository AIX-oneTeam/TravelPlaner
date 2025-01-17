from app.utils.naver_utils import get_naver_access_token, get_naver_user_profile

class NaverOAuthService:
    @staticmethod
    async def authenticate_user(code: str, state: str):
        token_data = await get_naver_access_token(code, state)
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError("Access token not found")

        user_profile = await get_naver_user_profile(access_token)
        return user_profile
