import os
from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get YouTube API key from environment
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

def extract_video_id(url):
    parsed_url = urlparse(url)

    if parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
        if parsed_url.path == '/watch':
            # Normal YouTube video
            return parse_qs(parsed_url.query).get('v', [None])[0]
        elif parsed_url.path.startswith('/shorts/'):
            # YouTube Shorts
            return parsed_url.path.split('/shorts/')[1].split('/')[0]
    elif parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]
    return None

def fetch_youtube_comments(video_url, max_comments=100):
    if not YOUTUBE_API_KEY:
        raise Exception("❌ YouTube API key not found. Please set 'YOUTUBE_API_KEY' in your .env file.")

    video_id = extract_video_id(video_url)
    if not video_id:
        print("❌ Invalid YouTube URL or unable to extract video ID")
        return []

    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

    comments = []
    next_page_token = None

    while len(comments) < max_comments:
        request = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            maxResults=min(100, max_comments - len(comments)),
            pageToken=next_page_token,
            textFormat='plainText'
        )
        response = request.execute()

        for item in response.get('items', []):
            comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
            comments.append(comment)

        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break

    return comments
