import sys
import os

sys.path.append(os.path.dirname(__file__))

from url_identifier import identify_url_type
from reddit_scraper import fetch_reddit_comments
from instagram_scraper import fetch_instagram_comments
from youtube_scraper import fetch_youtube_comments

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
            comments = fetch_reddit_comments(comment_url)

        elif platform == "Instagram Post":
            comments = fetch_instagram_comments(comment_url)

        elif platform == "YouTube Video":
            comments = fetch_youtube_comments(comment_url)

        else:
            print("⚠️ Unknown or unsupported URL format.")
            comments = []

        return comments

    except Exception as e:
        print(f"❌ Error in fetching comments: {e}")
        return []
