import requests
import os
import shutil
import re

def extract_deviation_id(url):
    """
    Extract deviation ID from DeviantArt URL.
    Supports formats like:
    - https://www.deviantart.com/user/art/title-1234567890
    - https://www.deviantart.com/user/art/1234567890
    """
    match = re.search(r'/art/(?:.*-)?(\d+)$', url.rstrip('/'))
    if match:
        return match.group(1)
    return None

def download_image(page_url):
    try:
        access_token = os.getenv("DEVIANTART_ACCESS_TOKEN")
        if not access_token:
            raise EnvironmentError("Missing DEVIANTART_ACCESS_TOKEN in environment variables.")

        deviation_id = extract_deviation_id(page_url)
        if not deviation_id:
            raise ValueError("Could not extract deviation ID from URL.")

        print(f"[INFO] Extracted deviation ID: {deviation_id}")

        api_url = f"https://www.deviantart.com/api/v1/oauth2/deviation/download/{deviation_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()

        data = response.json()
        if "src" not in data:
            raise ValueError("Download not allowed or image not found in API response.")

        image_url = data["src"]
        filename = os.path.basename(image_url.split('?')[0])
        if not filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            filename += '.png'

        downloads_folder = os.path.join(os.getcwd(), 'deviantart_downloads')
        os.makedirs(downloads_folder, exist_ok=True)
        image_path = os.path.join(downloads_folder, filename)

        print(f"[INFO] Downloading image from: {image_url}")

        img_response = requests.get(image_url, stream=True, headers={"User-Agent": "Mozilla/5.0"})
        img_response.raise_for_status()

        if not img_response.headers.get('content-type', '').startswith('image'):
            raise ValueError("Downloaded content is not an image.")

        with open(image_path, 'wb') as out_file:
            shutil.copyfileobj(img_response.raw, out_file)

        print(f"[SUCCESS] Image downloaded to: {image_path}")

        return {"success": True, "image_path": image_path}

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return {"success": False, "error": str(e)}
