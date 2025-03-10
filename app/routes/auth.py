from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
import google_auth_oauthlib.flow
from fastapi.responses import JSONResponse
import os
import json

router = APIRouter()
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
# Google OAuth settings
CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/adwords"]
REDIRECT_URI = "http://localhost:8000/auth/callback"

@router.get("/login")
async def login():
    """Redirects the user to Google OAuth login page"""
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(access_type="offline", include_granted_scopes="true")
    return RedirectResponse(auth_url)

TOKEN_FILE = "token.json"  # File where tokens will be saved

@router.get("/callback")
async def callback(request: Request):
    """Handles OAuth callback and saves the access token."""
    try:
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI
        )

        # Get full request URL with the auth code
        auth_response = str(request.url)
        print(f"Received OAuth response: {auth_response}")

        # Exchange the authorization code for an access token
        flow.fetch_token(authorization_response=auth_response)

        credentials = flow.credentials
        access_token = credentials.token
        refresh_token = credentials.refresh_token
        expiry = credentials.expiry.isoformat()  # Convert expiry time to a string

        # Save tokens to a file
        token_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expiry": expiry
        }

        with open(TOKEN_FILE, "w") as f:
            json.dump(token_data, f)

        print("Access token saved successfully!")

        return JSONResponse({"message": "Authentication Successful!", "access_token": access_token})

    except Exception as e:
        print(f"Error during OAuth callback: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)