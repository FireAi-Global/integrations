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
DEVELOPER_TOKEN = "NUq5rU8nbcjMT3EEtK60MA"      # Permanent token.

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

        print("OAuth Token Fetched Successfully")

        # Attempt to fetch customer ID WITHOUT the try-except (for debugging)
        google_ads_client = GoogleAdsClient.load_from_dict({
            "developer_token": DEVELOPER_TOKEN,
            "refresh_token": credentials.refresh_token,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "use_proto_plus": True,
        })
        # Use GoogleAdsService to get customer ID
        google_ads_service = google_ads_client.get_service("GoogleAdsService")

        query = """
            SELECT customer.id FROM customer LIMIT 1
        """

        request = google_ads_client.get_type("SearchGoogleAdsRequest")
        # Get CustomerService to fetch the correct customer ID
        customer_service = google_ads_client.get_service("CustomerService")

        # Fetch login customer ID
        login_customer_id = customer_service.list_accessible_customers().resource_names[0].split("/")[-1]

        # Use the fetched customer ID for the request
        request.customer_id = login_customer_id

        request.query = query

        response = google_ads_service.search(request=request)

        # Extract Customer ID
        customer_id = None
        for row in response:
            customer_id = row.customer.id

        if not customer_id:
            raise Exception("Customer ID could not be retrieved. Ensure you have the right permissions.")

        token_data["customer_id"] = customer_id
        print(f"Successfully fetched Customer ID: {customer_id}")

        token_data["customer_id"] = customer_id
        print(f"Successfully fetched initial Customer ID: {customer_id}")

        # Save credentials including customer_id
        with open("google_ads_credentials.json", "w") as token_file:
            json.dump(token_data, token_file)
            print("Credentials saved to file")

        return {"message": "✅ Login successful!", "refresh_token": credentials.refresh_token, "customer_id": customer_id if 'customer_id' in token_data else "Customer ID could not be retrieved"}
    except Exception as e:
        print(f"OAuth Callback Failed (Outer Exception): {e}")
        return {"error": f"OAuth Callback Failed: {str(e)}"}
    
# Step 3: Fetch Google Ads Account Details
@app.get("/account-details")
async def get_account_details():
    """Fetches account details (Manager or Direct Client Account)."""

    # Load stored credentials
    try:
        with open("google_ads_credentials.json", "r") as token_file:
            credentials_data = json.load(token_file)
            customer_id = credentials_data.get("customer_id")
            if not customer_id:
                return {"error": "Customer ID not found in credentials. Please log in again."}
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
            "login_customer_id": customer_id  # Important: Specify the customer ID for API calls
        })

        service = google_ads_client.get_service("GoogleAdsService")

        # Query to check if account is Manager or Client
        query = """
        SELECT customer.id, customer.descriptive_name, customer.manager
        FROM customer
        """

        response = service.search(customer_id=str(customer_id), query=query)

        accounts = []
        manager_id = None

        for row in response:
            cust_id = row.customer.id
            customer_name = row.customer.descriptive_name
            is_manager = row.customer.manager

            accounts.append({"id": cust_id, "name": customer_name, "is_manager": is_manager})

            if is_manager:
                manager_id = cust_id

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

    response = service.search(customer_id=str(manager_customer_id), query=query)


    clients = [{"id": row.customer_client.id, "name": row.customer_client.descriptive_name} for row in response]

    return clients

# Step 5: Fetch Campaigns for a Specific Customer ID -> Query to be taken from USER
@app.get("/details/{linked_account_id}")
async def get_campaign_details(linked_account_id: str):
    """Fetches campaign details for the given linked account ID while using login_customer_id."""

    # Load stored credentials
    try:
        with open("google_ads_credentials.json", "r") as token_file:
            credentials_data = json.load(token_file)
            login_customer_id = credentials_data.get("customer_id")
            if not login_customer_id:
                return {"error": "Login Customer ID not found. Please log in again."}
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
            "login_customer_id": str(login_customer_id)  # Use the login customer ID
        })

        service = google_ads_client.get_service("GoogleAdsService")

        # Query to fetch campaign details for the given linked account
        query = """
        SELECT 
            campaign.id, 
            campaign.name, 
            campaign.status, 
            campaign.start_date, 
            campaign.end_date
        FROM campaign
        """

        response = service.search(customer_id=str(linked_account_id), query=query)

        campaigns = []
        for row in response:
            campaigns.append({
                "id": row.campaign.id,
                "name": row.campaign.name,
                "status": row.campaign.status.name,
                "start_date": row.campaign.start_date,
                "end_date": row.campaign.end_date
            })

        if not campaigns:
            return {"message": "No campaigns found for this account."}

        return {"linked_account_id": linked_account_id, "campaigns": campaigns}

    except Exception as e:
        return {"error": f"Failed to fetch campaign details: {str(e)}"}

# Run FastAPI Server
if __name__ == "__main__":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # ✅ Set this to allow HTTP in local testing
    uvicorn.run(app, host="localhost", port=8000, reload=True)