import os
import re
import requests
from urllib.parse import urlparse
import logging

logging.basicConfig(level=logging.INFO)

# Read config from Render environment variables
CLIENT_ID = os.getenv("DA_CLIENT_ID")
CLIENT_SECRET = os.getenv("DA_CLIENT_SECRET")
REDIRECT_URI = os.getenv("DA_REDIRECT_URI")
REFRESH_TOKEN = os.getenv("DA_REFRESH_TOKEN")

# Fetch access token using refresh_token
def get_access_token():
    url = "https://www.deviantart.com/oauth2/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "redirect_uri": REDIRECT_URI,
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json().get("access_token")

# Fetch comments using DeviantArt API
def fetch_comments(deviation_url, max_comments=10):
    try:
        access_token = get_access_token()
        deviation_id = deviation_url.strip("/").split("-")[-1]

        headers = {"Authorization": f"Bearer {access_token}"}
        api_url = f"https://www.deviantart.com/api/v1/oauth2/comments/deviation/{deviation_id}?limit={max_comments}"

        response = requests.get(api_url, headers=headers)
        response.raise_for_status()

        comments = response.json().get("thread", [])
        return [comment["comment"]["body"] for comment in comments if "comment" in comment]

    except Exception as e:
        logging.error(f"Error fetching comments: {e}")
        return []
