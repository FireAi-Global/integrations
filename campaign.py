from google.ads.googleads.client import GoogleAdsClient  

# Load Google Ads client from yaml configuration
client = GoogleAdsClient.load_from_storage("google-ads.yaml")

def fetch_all_client_accounts(manager_customer_id):
    """Fetch all client accounts under the manager account."""
    
    query = """
    SELECT 
      customer_client.client_customer, 
      customer_client.descriptive_name
    FROM customer_client
    WHERE customer_client.level != 0  # Exclude the manager account itself
    """

    service = client.get_service("GoogleAdsService")

    request = client.get_type("SearchGoogleAdsRequest")
    request.customer_id = manager_customer_id  # Use the manager account ID
    request.query = query

    response = service.search(request=request)

    print(f"📢 Accessible Clients under Manager ID {manager_customer_id}:")

    client_accounts = []
    for row in response:
        client_id = row.customer_client.client_customer
        client_name = row.customer_client.descriptive_name
        client_accounts.append((client_id, client_name))
        print(f"📌 Client ID: {client_id}, Name: {client_name}")

    return client_accounts

# Replace with your Manager Account ID
manager_customer_id = "3926789319"
fetch_all_client_accounts(manager_customer_id)
