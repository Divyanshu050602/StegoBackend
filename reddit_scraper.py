# scrape_comments.py

import praw

def fetch_reddit_comments(post_url: str, limit=10):
    reddit = praw.Reddit(
        client_id='MAjsFIXJ5oJmx4Ojz1ZZ_g',
        client_secret='UWqLP3pVRCo8BWjetOfhbqH1yrBxgA',
        user_agent='comment-scraper'
    )

    try:
        submission = reddit.submission(url=post_url)
        submission.comments.replace_more(limit=0)
        comments = [comment.body for comment in submission.comments[:limit]]
        return comments
    except Exception as e:
        print("❌ Error:", e)
        return []

# Example usage
if __name__ == "__main__":
    url = input("Enter Reddit Post URL: ")
    comments = fetch_reddit_comments(url)
    print("\n📌 Extracted Comments:")
    for i, comment in enumerate(comments, 1):
        print(f"{i}. {comment}")
