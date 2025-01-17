from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from services.google_oauth_service import get_google_authorization_url, handle_google_callback
from test_db import get_db

router = APIRouter()

@router.get("/google/login")
async def google_login():
    """Redirect user to Google OAuth login page."""
    try:
        authorization_url = get_google_authorization_url()
        return RedirectResponse(authorization_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate Google login URL: {e}")

@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback and process user login."""
    try:
        request_url = str(request.url)
        response_data = handle_google_callback(request_url, db)
        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google OAuth callback failed: {e}")
