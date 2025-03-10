import requests
from fastapi import APIRouter, HTTPException
import json

router = APIRouter()

# Load credentials
TOKEN_FILE = "token.json"

def get_access_token():
    """Load access token from token.json"""
    try:
        with open(TOKEN_FILE, "r") as token_file:
            token_data = json.load(token_file)

        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=401, detail="Access token not found in token.json")

        return access_token
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Error reading access token: {str(e)}")

def get_accessible_customers(access_token):
    """Fetch accessible customers using direct HTTP request."""
    url = "https://googleads.googleapis.com/v19/customers:listAccessibleCustomers"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": "DUMMY_TOKEN",
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"Google Ads API error: {response.text}")

    data = response.json()
    return [name.split("/")[-1] for name in data.get("resourceNames", [])]

@router.get("/campaigns")
async def get_campaigns():
    """Fetch Google Ads campaigns using direct HTTP request."""
    access_token = get_access_token()

    try:
        customer_ids = get_accessible_customers(access_token)
    except HTTPException as e:
        return {"error": str(e.detail)}

    if not customer_ids:
        return {"error": "No accessible customer IDs found"}

    results = []
    for customer_id in customer_ids:
        url = f"https://googleads.googleapis.com/v19/customers/{customer_id}/googleAds:search"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "developer-token": "DUMMY_TOKEN",
            "Content-Type": "application/json",
        }
        payload = {
            "query": "SELECT campaign.id, campaign.name, campaign.status FROM campaign"
        }

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            data = response.json()
            for row in data.get("results", []):
                results.append({
                    "customer_id": customer_id,
                    "campaign_id": row["campaign"]["id"],
                    "campaign_name": row["campaign"]["name"],
                    "status": row["campaign"]["status"],
                })
        else:
            print(f"Error fetching campaigns for {customer_id}: {response.text}")

    if not results:
        return {"error": "No campaigns found"}

    return results
