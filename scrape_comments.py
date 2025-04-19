import requests
from bs4 import BeautifulSoup
import re

def get_deviation_id(url):
    patterns = [
        r'/art/[\w-]+-(\d+)',
        r'/deviation/(\d+)',
        r'/gallery/(\d+)',
        r'deviationid=(\d+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_comments_html(url):
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        comments = []
        # Modern structure
        for comment in soup.find_all('div', {'data-hook': 'comment_extractor'}):
            try:
                username = comment.find('a', {'data-hook': 'username'})
                username = username.text.strip() if username else "Anonymous"
                text_div = comment.find('div', {'data-hook': 'comment_extractor-body'})
                comment_text = ' '.join(text_div.stripped_strings) if text_div else ''
                comments.append({"username": username, "comment": comment_text})
            except Exception:
                continue

        # Fallback to legacy structure
        if not comments:
            for c in soup.find_all('div', class_='_2ZtHP'):
                try:
                    username = c.find('a', class_='_277bf')
                    username = username.text.strip() if username else "Anonymous"
                    text_div = c.find('div', class_='_1LEaS')
                    comment_text = ' '.join(text_div.stripped_strings) if text_div else ''
                    comments.append({"username": username, "comment": comment_text})
                except Exception:
                    continue

        return comments or [{"error": "No comments found"}]

    except Exception as e:
        return [{"error": str(e)}]
