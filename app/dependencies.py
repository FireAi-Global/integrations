from google_auth_oauthlib.flow import Flow
from fastapi import Depends
import google.auth.transport.requests

from app.config import CLIENT_SECRETS_FILE, SCOPES

def get_google_auth_flow():
    """Initialize Google OAuth Flow"""
    return Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri="http://localhost:8000/auth/callback"
    )

def refresh_token(credentials):
    """Refresh expired Google OAuth token"""
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
