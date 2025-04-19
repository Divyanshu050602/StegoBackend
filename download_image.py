import requests
import os
import shutil
from bs4 import BeautifulSoup

def download_image(page_url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        page_response = requests.get(page_url, headers=headers)
        page_response.raise_for_status()

        # Parse the HTML to find og:image meta tag
        soup = BeautifulSoup(page_response.text, 'html.parser')
        meta_tag = soup.find('meta', property='og:image')
        if not meta_tag or not meta_tag.get('content'):
            return {"success": False, "error": "Could not find image (og:image not found)."}

        image_url = meta_tag['content']

        # Extract a safe filename
        filename = os.path.basename(image_url.split('?')[0])
        if not filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            filename += '.png'

        # Ensure deviantart_downloads folder exists
        downloads_folder = os.path.join(os.getcwd(), 'deviantart_downloads')
        os.makedirs(downloads_folder, exist_ok=True)
        image_path = os.path.join(downloads_folder, filename)

        # Download the image
        response = requests.get(image_url, stream=True, headers=headers)
        response.raise_for_status()

        if not response.headers.get('content-type', '').startswith('image'):
            return {"success": False, "error": "URL does not point to an image."}

        with open(image_path, 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)

        return {"success": True, "image_path": image_path}

    except Exception as e:
        return {"success": False, "error": str(e)}
