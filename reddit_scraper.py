import os
import praw

# Get Reddit API credentials from environment
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "comment-scraper")

def fetch_reddit_comments(post_url):
    if not all([REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT]):
        raise Exception("❌ Missing Reddit API credentials. Please set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, and REDDIT_USER_AGENT in your .env file.")

    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT
    )

    try:
        submission = reddit.submission(url=post_url)
        submission.comments.replace_more(limit=0)
        comments = [comment.body for comment in submission.comments[:limit]]
        return comments
    except Exception as e:
        print(f"❌ Error fetching Reddit comments: {e}")
        return []
