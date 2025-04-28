import os
from apify_client import ApifyClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Apify token from environment
APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")

def fetch_instagram_comments(instagram_url):
    if not APIFY_TOKEN:
        raise Exception("❌ Apify API token not found. Make sure 'APIFY_API_TOKEN' is set in .env.")

    # Initialize Apify client
    client = ApifyClient(APIFY_TOKEN)

    run_input = {
        "directUrls": [instagram_url],
        "resultsLimit": 1000,
        "scrollWaitSecs": 3,
        "proxy": {"useApifyProxy": True},
    }

    # Start the actor
    try:
        run = client.actor("apify/instagram-comment-scraper").call(run_input=run_input)
    except Exception as e:
        print(f"❌ Error triggering Apify actor: {e}")
        return []

    comments_list = []
    try:
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            comment = item.get("text")
            if comment:
                comments_list.append(comment)
    except Exception as e:
        print(f"❌ Error fetching results: {e}")
        return []

    return comments_list
