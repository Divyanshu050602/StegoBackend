import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.dirname(__file__))

from url_identifier import identify_url_type
from reddit_scraper import fetch_reddit_comments
from instagram_scraper import get_instagram_comments
from youtube_scraper import fetch_comments as fetch_youtube_comments

# Load environment variables from .env
load_dotenv()

# Load API keys from environment
APIFY_TOKEN = os.getenv("APIFY_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

def fetch_comments(comment_url):
    """
    Main function called by decrypt_handler.
    Accepts a comment_url and routes it to the appropriate scraper.
    Returns a list of extracted comments.
    """
    try:
        platform = identify_url_type(comment_url)
        print(f"🔎 Identified platform: {platform}")

        if platform == "Reddit Post":
            comments = fetch_reddit_comments(comment_url, limit=100)

        elif platform == "Instagram Post":
            if not APIFY_TOKEN:
                print("⚠️ Apify API token missing.")
                return []
            comments = get_instagram_comments(comment_url, apify_token=APIFY_TOKEN)

        elif platform == "YouTube Video":
            if not YOUTUBE_API_KEY:
                print("⚠️ YouTube API key missing.")
                return []
            comments = fetch_youtube_comments(comment_url, api_key=YOUTUBE_API_KEY)

        else:
            print("⚠️ Unknown or unsupported URL format.")
            comments = []

        return comments

    except Exception as e:
        print(f"❌ Error in fetching comments: {e}")
        return []
