import requests
from fastapi import APIRouter, HTTPException
import json

router = APIRouter()

# Load credentials
TOKEN_FILE = "token.json"
DEVELOPER_TOKEN = "NUq5rU8nbcjMT3EEtK60MA"  # Replace with your actual developer token

def get_access_token():
    """Load access token from token.json"""
    try:
        with open(TOKEN_FILE, "r") as token_file:
            token_data = json.load(token_file)

        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=401, detail="Access token not found in token.json")

        print(f"Using Access Token: {access_token}")  # Debugging
        return access_token
    except FileNotFoundError:
        raise HTTPException(status_code=401, detail=f"Error: {TOKEN_FILE} not found.")
    except json.JSONDecodeError:
        raise HTTPException(status_code=401, detail=f"Error: Invalid JSON in {TOKEN_FILE}.")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Error reading access token: {str(e)}")

def get_accessible_customers(access_token):
    """Fetch accessible customers using direct HTTP request."""
    url = "https://googleads.googleapis.com/v19/customers:listAccessibleCustomers"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": DEVELOPER_TOKEN,
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"Google Ads API error (listAccessibleCustomers): {response.text}")

    data = response.json()
    return [name.split("/")[-1] for name in data.get("resourceNames", [])]

@router.get("/campaigns")
async def get_campaigns():
    """Fetch Google Ads campaigns using direct HTTP request."""
    access_token = get_access_token()

    try:
        customer_ids = get_accessible_customers(access_token)
        print(f"Accessible Customer IDs: {customer_ids}")
    except HTTPException as e:
        return {"error": str(e.detail)}

    if not customer_ids:
        return {"error": "No accessible customer IDs found"}

    print(f"Customer IDs: {customer_ids}")  # Debugging output
    all_campaigns = []
    for customer_id in customer_ids:
        url = f"https://googleads.googleapis.com/v19/customers/{customer_id}/googleAds:search"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "developer-token": DEVELOPER_TOKEN,
            "Content-Type": "application/json",
            "login-customer-id": customer_id,  # Use the current customer_id as login customer ID
        }
        payload = {
            "query": """
            SELECT campaign.id, campaign.name, campaign.status, campaign.advertising_channel_type FROM campaign
            """
        }

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response Data for Customer ID {customer_id}: {json.dumps(data, indent=2)}")
                campaigns = data.get("results", [])
                print(f"Number of Campaigns found for Customer ID {customer_id}: {len(campaigns)}")
                for row in campaigns:
                    campaign_data = row.get("campaign")
                    if campaign_data:
                        all_campaigns.append({
                            "customer_id": customer_id,
                            "campaign_id": campaign_data.get("id"),
                            "campaign_name": campaign_data.get("name"),
                            "status": campaign_data.get("status"),
                            "advertising_channel_type": campaign_data.get("advertisingChannelType"),
                        })
            except json.JSONDecodeError:
                print(f"Error decoding JSON response for Customer ID {customer_id}: {response.text}")
        else:
            print(f"Error fetching campaigns for Customer ID {customer_id}: Status Code: {response.status_code}, Response: {response.text}")
        break  # Remove this break to fetch campaigns for all accessible customers
    return all_campaigns if all_campaigns else {"error": "No campaigns found across all accessible accounts"}