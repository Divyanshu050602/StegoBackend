import requests
import os
import shutil
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def download_image(image_url):
    try:
        # Step 1: Fetch the DeviantArt HTML page
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        response = requests.get(image_url, headers=headers)
        response.raise_for_status()
        html = response.text

        # Step 2: Parse the HTML and extract the image URL
        soup = BeautifulSoup(html, 'html.parser')
        img_tag = soup.find('img', class_='dev-content-full')
        if not img_tag or not img_tag.get('src'):
            return {"success": False, "error": "Could not find image on the page."}

        actual_image_url = img_tag['src']

        # Step 3: Determine filename from image src
        parsed_url = urlparse(actual_image_url)
        filename = os.path.basename(parsed_url.path)
        if not filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            filename += '.png'

        # Step 4: Setup download path
        downloads_folder = os.path.join(os.getcwd(), 'deviantart_downloads')
        os.makedirs(downloads_folder, exist_ok=True)
        image_path = os.path.join(downloads_folder, filename)

        # Step 5: Download the actual image
        img_response = requests.get(actual_image_url, stream=True)
        img_response.raise_for_status()

        if not img_response.headers.get('content-type', '').startswith('image'):
            return {"success": False, "error": "Extracted URL is not an image."}

        with open(image_path, 'wb') as out_file:
            shutil.copyfileobj(img_response.raw, out_file)

        return {"success": True, "image_path": image_path}

    except Exception as e:
        return {"success": False, "error": f"Error downloading image: {e}"}
