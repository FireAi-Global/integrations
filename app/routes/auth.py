from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
import google_auth_oauthlib.flow
import os
import json

router = APIRouter()

# Allow insecure transport for local development
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Google OAuth settings
CLIENT_SECRETS_FILE = "client_secret.json"
# SCOPES = ["https://www.googleapis.com/auth/adwords"]
SCOPES = [
    "https://www.googleapis.com/auth/adwords",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
]

REDIRECT_URI = "http://localhost:8000/auth/callback"
TOKEN_FILE = "token.json"  # File where tokens will be saved
STATE_FILE = "oauth_state.txt"  # File to store OAuth state

@router.get("/login")
async def login():
    """Redirects the user to Google OAuth login page"""
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI
    )
    authorization_url, state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true"
    )

    # Save state for verification in callback
    with open(STATE_FILE, "w") as f:
        f.write(state)

    return RedirectResponse(authorization_url)

@router.get("/callback")
async def callback(request: Request, state: str):
    """Handles OAuth callback and saves the access token."""
    try:
        # Verify the state
        if not os.path.exists(STATE_FILE):
            raise HTTPException(status_code=400, detail="State file missing")

        with open(STATE_FILE, "r") as f:
            stored_state = f.read().strip()

        if state != stored_state:
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        os.remove(STATE_FILE)  # Remove state file after use

        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI, state=state
        )

        # Use request.url._url instead of manually constructing the auth_response
        flow.fetch_token(authorization_response=str(request.url))

        credentials = flow.credentials
        access_token = credentials.token
        refresh_token = credentials.refresh_token
        expiry = credentials.expiry.isoformat() if credentials.expiry else None

        # Save tokens to a file
        token_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expiry": expiry,
        }

        with open(TOKEN_FILE, "w") as f:
            json.dump(token_data, f)

        print("Access token saved successfully!")

        return JSONResponse({"message": "Authentication Successful!", "access_token": access_token})

    except Exception as e:
        print(f"Error during OAuth callback: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
