import os
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv
import jwt
import requests
import logging
from ...utils.jwt_utils import create_token_from_oauth, create_refresh_token

# 로거 설정
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Load .env variables
load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

# 디버깅 로그 추가
logger.debug(f"GOOGLE_CLIENT_ID: {GOOGLE_CLIENT_ID}")
logger.debug(f"GOOGLE_REDIRECT_URI: {GOOGLE_REDIRECT_URI}")

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
    ],
    redirect_uri=GOOGLE_REDIRECT_URI,
)

async def get_google_authorization_url() -> str:
    """Generate Google authorization URL."""
    authorization_url, state = flow.authorization_url()
    return authorization_url


async def handle_google_callback(request_url: str) -> dict:
    """Handle Google OAuth callback and process user data."""
    try:
        logger.info("Starting Google callback handling process")
        
        # Fetch token from Google
        flow.fetch_token(authorization_response=request_url)
        credentials = flow.credentials

        # Decode ID token to get user info
        decoded_token = jwt.decode(credentials.id_token, options={"verify_signature": False})
        logger.debug(f"Decoded token: {decoded_token}")

        # Extract user information
        user_info = {
            "id": decoded_token.get("sub"),
            "name": decoded_token.get("name"),
            "email": decoded_token.get("email"),
            "picture": decoded_token.get("picture")
        }

        # Get additional user info using People API
        try:
            response = requests.get(
                "https://people.googleapis.com/v1/people/me",
                headers={"Authorization": f"Bearer {credentials.token}"},
                params={"personFields": "nicknames"}
            )
            if response.status_code == 200:
                people_data = response.json()
                nickname = people_data.get("nicknames", [{}])[0].get("value")
                if nickname:
                    user_info["nickname"] = nickname
        except Exception as e:
            logger.warning(f"Failed to fetch additional user info: {str(e)}")

        # Create JWT tokens
        jwt_token = create_token_from_oauth("google", user_info)
        refresh_token = create_refresh_token(user_info)

        user_data = {
            "jwt_token": jwt_token,
            "refresh_token": refresh_token,
            "user_info": user_info
        }
        return user_data

    except Exception as e:
        logger.error(f"Error processing Google callback: {str(e)}", exc_info=True)
        raise Exception(f"Failed to process Google callback: {str(e)}")
