import requests
from bs4 import BeautifulSoup
import re
import logging
from timeout_decorator import timeout, TimeoutError

# Set up logging
logging.basicConfig(level=logging.ERROR, filename='error_log.log',
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Timeout decorator (10 seconds timeout for the function)
@timeout(10)
def get_deviation_id(url):
    patterns = [
        r'/art/[\w-]+-(\d+)',
        r'/deviation/(\d+)',
        r'/gallery/(\d+)',
        r'deviationid=(\d+)'
    ]
    try:
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    except Exception as e:
        logging.error(f"Error in get_deviation_id: {str(e)}")
        return None

@timeout(10)
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
            except Exception as inner_exception:
                logging.error(f"Error processing comment in modern structure: {str(inner_exception)}")
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
                except Exception as inner_exception:
                    logging.error(f"Error processing comment in legacy structure: {str(inner_exception)}")
                    continue

        if not comments:
            logging.error(f"No comments found for URL: {url}")
            return [{"error": "No comments found"}]

        return comments

    except TimeoutError:
        error_msg = f"Request timed out while fetching comments from {url}"
        logging.error(error_msg)
        return [{"error": error_msg}]
    except Exception as e:
        error_msg = f"Error fetching comments from {url}: {str(e)}"
        logging.error(error_msg)
        return [{"error": error_msg}]
