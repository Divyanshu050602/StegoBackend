import requests
import os
from urllib.parse import urlparse, unquote

def convert_blob_to_raw(url):
    """Convert a GitHub blob URL to a raw content URL."""
    if "github.com" in url and "/blob/" in url:
        url = url.replace("github.com", "raw.githubusercontent.com")
        url = url.replace("/blob/", "/")
    return url

def download_image(image_url, save_dir='github_downloads'):
    try:
        image_url = convert_blob_to_raw(image_url)
        headers = {"User-Agent": "Mozilla/5.0"}

        # Extract and validate filename
        parsed_url = urlparse(image_url)
        filename = os.path.basename(unquote(parsed_url.path))
        valid_extensions = ('.png', '.jpg', '.jpeg', '.webp')
        if not filename.lower().endswith(valid_extensions):
            return {"success": False, "error": "URL does not point to a valid image file"}

        # Create output directory
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, filename)

        # Download the file
        response = requests.get(image_url, stream=True, headers=headers)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if not (content_type.startswith("image") or content_type == "application/octet-stream"):
            return {"success": False, "error": f"Unexpected content-type: {content_type}"}

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)

        return {"success": True, "image_path": file_path}

    except Exception as e:
        return {"success": False, "error": str(e)}
