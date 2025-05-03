import requests
import os
import shutil
import re

def extract_deviation_id(url):
    """Extract deviation ID from DeviantArt URL."""
    match = re.search(r'/art/(?:.*-)?(\d+)(?:/?|$)', url)
    if match:
        return match.group(1)
    return None

def download_image(page_url):
    try:
        # Get token from environment
        access_token = os.getenv("DEVIANTART_ACCESS_TOKEN")
        if not access_token:
            return {
                "success": False,
                "error": "Missing DeviantArt access token in environment variables."
            }

        deviation_id = extract_deviation_id(page_url)
        if not deviation_id:
            return {
                "success": False,
                "error": "Could not extract deviation ID from URL."
            }

        # Call DeviantArt download API
        api_url = f"https://www.deviantart.com/api/v1/oauth2/deviation/download/{deviation_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()

        data = response.json()
        if "src" not in data:
            return {
                "success": False,
                "error": "Download not allowed or image not found in API response."
            }

        image_url = data["src"]
        filename = os.path.basename(image_url.split('?')[0])
        if not filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            filename += '.png'

        downloads_folder = os.path.join(os.getcwd(), 'deviantart_downloads')
        os.makedirs(downloads_folder, exist_ok=True)
        image_path = os.path.join(downloads_folder, filename)

        # Download image content
        img_response = requests.get(image_url, stream=True, headers={"User-Agent": "Mozilla/5.0"})
        img_response.raise_for_status()

        if not img_response.headers.get('content-type', '').startswith('image'):
            return {
                "success": False,
                "error": "Downloaded content is not an image."
            }

        with open(image_path, 'wb') as out_file:
            shutil.copyfileobj(img_response.raw, out_file)

        print("SUCCESS: Image downloaded")
        return {
            "success": True,
            "image_path": image_path
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
