# url_identifier.py

import re

def identify_url_type(url: str) -> str:
    """
    Identify whether a URL is a Reddit post, YouTube video (normal or shorts), or Instagram post.

    Args:
        url (str): The input URL.

    Returns:
        str: Platform type ("Reddit Post", "YouTube Video", "Instagram Post", or "Unknown")
    """
    url = url.strip().lower()

    patterns = {
        "Reddit Post": r"(https?://)?(www\.)?reddit\.com/r/[\w\d_]+/comments/[\w\d]+",
        "YouTube Video": r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w\-]+",
        "Instagram Post": r"(https?://)?(www\.)?instagram\.com/(p|reel|tv)/[\w\-]+/?",
    }

    for platform, pattern in patterns.items():
        if re.search(pattern, url):      # ✅ use re.search, not re.match
            return platform

    return "Unknown"
