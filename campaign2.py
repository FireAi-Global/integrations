import json
import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from google_auth_oauthlib.flow import InstalledAppFlow
from google.ads.googleads.client import GoogleAdsClient

# FastAPI app instance
app = FastAPI()

# OAuth 2.0 Config
CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = [
    "https://www.googleapis.com/auth/adwords",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
]
REDIRECT_URI = "http://localhost:8000/callback"  # Ensure this is registered in Google Cloud Console

# Google Ads Developer Token
DEVELOPER_TOKEN = "NUq5rU8nbcjMT3EEtK60MA"

# Set up OAuth flow globally
flow = Flow.from_client_secrets_file(
    CLIENT_SECRETS_FILE,
    scopes=SCOPES,
    redirect_uri=REDIRECT_URI
)

# Step 1: Google OAuth Login
@app.get("/")
async def login():
    """Redirects user to Google OAuth login page."""
    auth_url, _ = flow.authorization_url(prompt="consent")  # ✅ Removed duplicate redirect_uri
    return RedirectResponse(auth_url)

# Step 2: Handle OAuth Callback & Get Refresh Token
@app.get("/callback")
async def callback(request: Request):
    """Handles OAuth callback, fetches refresh token & saves credentials."""
    try:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES, redirect_uri=REDIRECT_URI)

        flow.fetch_token(
            authorization_response=str(request.url),
            include_granted_scopes=False  # Ensure only requested scopes are granted
        )

        credentials = flow.credentials
        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
        }

        # Save credentials
        with open("google_ads_credentials.json", "w") as token_file:
            json.dump(token_data, token_file)

        return {"message": "✅ Login successful!", "refresh_token": credentials.refresh_token}
    except Exception as e:
        return {"error": f"OAuth Callback Failed: {str(e)}"}

# Step 3: Fetch Google Ads Account Details
@app.get("/account-details")
async def get_account_details():
    """Fetches account details (Manager or Direct Client Account)."""

    # Load stored credentials
    try:
        with open("google_ads_credentials.json", "r") as token_file:
            credentials_data = json.load(token_file)
    except FileNotFoundError:
        return {"error": "Credentials file not found. Please log in first."}
    except json.JSONDecodeError:
        return {"error": "Invalid credentials file."}

    # Initialize Google Ads Client
    try:
        google_ads_client = GoogleAdsClient.load_from_dict({
            "developer_token": DEVELOPER_TOKEN,
            "refresh_token": credentials_data["refresh_token"],
            "client_id": credentials_data["client_id"],
            "client_secret": credentials_data["client_secret"],
            "use_proto_plus": True,
        })

        service = google_ads_client.get_service("GoogleAdsService")

        # Query to check if account is Manager or Client
        query = """
        SELECT customer.id, customer.descriptive_name, customer.manager
        FROM customer
        """

        request = google_ads_client.get_type("SearchGoogleAdsRequest")
        request.customer_id = "me"
        request.query = query

        response = service.search(request=request)

        accounts = []
        manager_id = None

        for row in response:
            customer_id = row.customer.id
            customer_name = row.customer.descriptive_name
            is_manager = row.customer.manager

            accounts.append({"id": customer_id, "name": customer_name, "is_manager": is_manager})

            if is_manager:
                manager_id = customer_id

        # If Manager Account, fetch linked clients
        if manager_id:
            clients = fetch_client_accounts(google_ads_client, manager_id)
            return {"manager_id": manager_id, "linked_clients": clients}

        return {"accounts": accounts}

    except Exception as e:
        return {"error": f"Failed to fetch account details: {str(e)}"}

# Step 4: Fetch Linked Client Accounts (If Manager)
def fetch_client_accounts(client, manager_customer_id):
    """Fetches all client accounts linked to a Manager Account."""

    service = client.get_service("GoogleAdsService")

    query = """
    SELECT customer_client.id, customer_client.descriptive_name
    FROM customer_client
    WHERE customer_client.manager != TRUE
    """

    request = client.get_type("SearchGoogleAdsRequest")
    request.customer_id = manager_customer_id
    request.query = query

    response = service.search(request=request)

    clients = [{"id": row.customer_client.id, "name": row.customer_client.descriptive_name} for row in response]

    return clients

# Run FastAPI Server
if __name__ == "__main__":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # ✅ Set this to allow HTTP in local testing
    uvicorn.run(app, host="localhost", port=8000, reload=True)