import requests
import os
import shutil
from urllib.parse import urlparse

def download_image(image_url):
    try:
        # Get the filename from the URL
        parsed_url = urlparse(image_url)
        filename = os.path.basename(parsed_url.path)

        # Ensure that the filename has an appropriate image extension if missing
        if not filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            filename += '.png'

        # Define the download folder path (Downloads/DeviantArt_Downloads)
        downloads_folder = os.path.join(os.path.expanduser('~'), 'Downloads', 'DeviantArt_Downloads')

        # Create the folder if it doesn't exist
        os.makedirs(downloads_folder, exist_ok=True)

        # Create the full path for the image
        image_path = os.path.join(downloads_folder, filename)

        # Send a GET request to download the image
        response = requests.get(image_url, stream=True)
        response.raise_for_status()  # Check if the request was successful

        # Save the image to the local disk
        with open(image_path, 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)

        return image_path

    except Exception as e:
        return f"Error downloading image: {e}"
