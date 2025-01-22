from google_auth_oauthlib.flow import Flow
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os
import jwt
import requests
<<<<<<< HEAD:app/services/google_oauth_service.py
# from ..models.member import Member
=======
from app.data_models.member import Member

>>>>>>> fe4647cdc2f6e99d3f20d20e04a1861d7f9eabfa:app/services/oauths/google_oauth_service.py

# Load .env variables
load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

# Allow insecure transport (for local development)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Initialize Google OAuth flow
flow = Flow.from_client_config(
    {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    },
    scopes=[
        'openid',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
      # 반환된 scope가 다르면 오류가 나서 추가 정보를 선택할 수 없고, 아예 다 넣거나 빼야함
      # 'https://www.googleapis.com/auth/user.gender.read',
      # 'https://www.googleapis.com/auth/user.birthday.read' 
    ],
    redirect_uri=GOOGLE_REDIRECT_URI,
)

def get_google_authorization_url():
    """Generate Google authorization URL."""
    authorization_url, state = flow.authorization_url(
        # 리프레시 토큰 발급할 경우 필요
        # access_type="offline", include_granted_scopes="true"
    )
    return authorization_url

def handle_google_callback(request_url: str, db: Session):
    """Handle Google OAuth callback, fetch user data, and process user."""
    try:
        # Fetch token from Google
        flow.fetch_token(authorization_response=request_url)
        credentials = flow.credentials

        # Decode ID token to get user info
        decoded_token = jwt.decode(credentials.id_token, options={"verify_signature": False})
        print("-------------")
        print(decoded_token) # sub가 구글이 주는 id임
        print("-------------")
        name = decoded_token.get("family_name") + decoded_token.get("given_name")
        email = decoded_token.get("email")
        picture = decoded_token.get("picture", None)
        # refresh_token = credentials.refresh_token
        # email_verified = decoded_token.get("email_verified", False)

        # 추가정보(닉네임, 성별, 생년월일)
        access_token = credentials.token
        # Access Token을 사용하여 People API 호출
        response = requests.get(
            "https://people.googleapis.com/v1/people/me",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"personFields": "nicknames"}  # nicknames 필드 요청
        )

        if response.status_code == 200:
            user_info = response.json()
            nickname = user_info.get("nicknames", [{}])[0].get("value", None)
            # gender = user_info['genders'][0]['value']
            # birthday_year = user_info['birthdays'][0]['date']['year']
            # birthday_month = user_info['birthdays'][0]['date']['month']
            # birthday_day = user_info['birthdays'][0]['date']['day']
        else:
            print(f"Failed to fetch nickname: {response.status_code} - {response.text}")

        # Check if user exists in the database
        existing_user = db.query(Member).filter(Member.email == email).first()

        if not existing_user:
            # Add new user to the database
            new_member = Member(name=name, email=email)
            db.add(new_member)
            db.commit()
            db.refresh(new_member)
            return {"message": "New user added", "member": {"name": new_member.name, "email": new_member.email}}
        else:
            return {"message": "Existing user logged in", "member": {"name": existing_user.name, "email": existing_user.email}}

    except Exception as e:
        print(f"Error during Google OAuth callback: {e}")
        raise e
