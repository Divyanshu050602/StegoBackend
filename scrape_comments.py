import requests
from bs4 import BeautifulSoup
import re
import json

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
        sections = soup.find_all('div', {'data-hook': 'comment_extractor'})
        for comment in sections:
            username = comment.find('a', {'data-hook': 'username'})
            username = username.text.strip() if username else "Anonymous"
            text_div = comment.find('div', {'data-hook': 'comment_extractor-body'})
            if text_div:
                comment_text = ' '.join(text_div.stripped_strings)
                comments.append((username, comment_text))

        if not comments:
            legacy = soup.find_all('div', class_='_2ZtHP')
            for c in legacy:
                username = c.find('a', class_='_277bf')
                username = username.text.strip() if username else "Anonymous"
                text_div = c.find('div', class_='_1LEaS')
                if text_div:
                    comment_text = ' '.join(text_div.stripped_strings)
                    comments.append((username, comment_text))

        return comments

    except Exception as e:
        return [("Error", str(e))]
