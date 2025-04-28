from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs

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


def fetch_comments(video_url, api_key, max_comments=100):
    video_id = extract_video_id(video_url)
    if not video_id:
        print("❌ Invalid YouTube URL or unable to extract video ID")
        return []

    youtube = build('youtube', 'v3', developerKey=api_key)

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


if __name__ == "__main__":
    # Example usage
    video_url = input("🔗 Enter YouTube video URL (normal or shorts): ").strip()
    api_key = "AIzaSyCw2g_4ArYBIgPGTdpnap6Z17ojjS_shrI"

    comments = fetch_comments(video_url, api_key)

    print("\n💬 Fetched Comments:\n")
    for i, comment in enumerate(comments, 1):
        print(f"{i}. {comment}")