import os
import cv2
import numpy as np
import base64
import time
import json
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from hashlib import sha256
from werkzeug.utils import secure_filename
import tempfile
from datetime import datetime
from download_image import download_image
from comment_scraper import fetch_comments
from NLP_comment_and_keyword_analyser import find_best_match
import re
import logging


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_TTL = 600  # 10 minutes
UPLOAD_FOLDER = 'uploads'
ENCRYPTED_FOLDER = 'encrypted'

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ENCRYPTED_FOLDER'] = ENCRYPTED_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ENCRYPTED_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return "✅ Backend is running!"

def generate_key(lat, lon, keyword, machine_id):
    key_data = f"{lat}_{lon}_{keyword}_{machine_id}"
    return sha256(key_data.encode()).digest()

def encrypt_message(message, key):
    iv = os.urandom(12)
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted_message = encryptor.update(message.encode()) + encryptor.finalize()
    return iv, encryptor.tag, base64.b64encode(encrypted_message).decode()

def hide_message_in_image(image_path, message, output_path, lat, lon, keyword, machine_id, start_timestamp, end_timestamp, ttl=DEFAULT_TTL):
    key = generate_key(lat, lon, keyword, machine_id)
    iv, tag, encrypted_message = encrypt_message(message, key)

    # Encrypt lat/lon
    iv_loc, tag_loc, encrypted_lat = encrypt_message(str(lat), key)
    _, _, encrypted_lon = encrypt_message(str(lon), key)

    data_dict = {
        'iv': base64.b64encode(iv).decode(),
        'tag': base64.b64encode(tag).decode(),
        'msg': encrypted_message,
        'start_timestamp': int(start_timestamp),
        'end_timestamp': int(end_timestamp),
        'ttl': ttl,
        'lat': encrypted_lat,
        'lon': encrypted_lon,
        'iv_loc': base64.b64encode(iv_loc).decode(),
        'tag_loc': base64.b64encode(tag_loc).decode()
    }

    data = base64.b64encode(json.dumps(data_dict).encode()).decode() + '###'

    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError("Invalid image path or unsupported format")

    height, width, _ = img.shape
    max_bytes = (height * width * 3) // 8

    if len(data) > max_bytes:
        raise ValueError("Message too large to hide in image")

    binary_message = ''.join(format(ord(c), '08b') for c in data)
    data_index = 0

    for row in img:
        for pixel in row:
            for channel in range(len(pixel)):
                if data_index < len(binary_message):
                    pixel[channel] = (pixel[channel] & 0xFE) | int(binary_message[data_index])
                    data_index += 1

    cv2.imwrite(output_path, img)


@app.route('/store-location', methods=['POST'])
def store_location():
    try:
        data = request.get_json()
        sender_email = data['senderEmail']
        latitude = data['latitude']
        longitude = data['longitude']
        device_id = data['deviceId']

        print(f"[Location Received] From: {sender_email}, Location: ({latitude}, {longitude}), Device ID: {device_id}")

        # Store only the required fields
        with open("location_temp.json", "w") as f:
            json.dump({
                "sender_email": sender_email,
                "latitude": latitude,
                "longitude": longitude,
                "device_id": device_id
            }, f)

        return jsonify({"message": "Location stored successfully!"}), 200

    except Exception as e:
        print(f"[ERROR] Failed to store location: {str(e)}")
        return jsonify({"error": "Failed to store location"}), 500


@app.route("/encrypt", methods=["POST"])
def encrypt_handler():
    try:
        # ✅ Step 1: Receive data from frontend
        image = request.files['image']
        message = request.form['message']
        keyword = request.form['keyword']
        start_timestamp_str = request.form['startTimestamp']
        end_timestamp_str = request.form['endTimestamp']

        start_dt = datetime.strptime(start_timestamp_str, "%Y-%m-%dT%H:%M")
        end_dt = datetime.strptime(end_timestamp_str, "%Y-%m-%dT%H:%M")
        start_timestamp = int(start_dt.timestamp())
        end_timestamp = int(end_dt.timestamp())

        # ✅ Step 2: Load stored geolocation and device data from location_temp.json
        with open("location_temp.json", "r") as f:
            location_data = json.load(f)

        lat = location_data.get("latitude")
        lon = location_data.get("longitude")
        machine_id = location_data.get("device_id")

        # ❗ Optional check
        if not all([lat, lon, machine_id]):
            return jsonify({"error": "Missing geolocation or device data. Please click the tracking link again."}), 400

        # ✅ Step 3: Save the uploaded image temporarily
        filename = secure_filename(image.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        encrypted_filename = "encrypted_" + os.path.splitext(filename)[0] + ".png"
        output_path = os.path.join(app.config['ENCRYPTED_FOLDER'], encrypted_filename)

        image.save(input_path)

        # ✅ Step 4: Encrypt the message into the image using all date
        hide_message_in_image(
            image_path=input_path, 
            message=message,
            output_path=output_path,
            lat=lat,
            lon=lon,
            keyword=keyword,
            machine_id=machine_id,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            ttl=DEFAULT_TTL
        )

        # ✅ Step 5: Send encrypted image back to frontend as a downloadable file
        return send_file(
            output_path,
            mimetype='image/png',
            as_attachment=True,
            download_name=encrypted_filename
        )

    except Exception as e:
        print(f"[ERROR] /encrypt: {e}")
        return jsonify({"error": str(e)}), 500


import re

def is_valid_ascii(s):
    try:
        s.encode('ascii')
        return True
    except UnicodeEncodeError:
        return False

@app.route('/decrypt', methods=['POST'])
def decrypt_handler():
    try:
        # 1. Extract data from frontend
        image_url = request.form.get('image_url')
        comment_url = request.form.get('comment_url')
        keyword = request.form.get('keyword')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        machine_id = request.form.get('machine_id')
        timestamp = request.form.get('timestamp')

        logger.info(f"Decryption attempt with: URL={image_url}, keyword={keyword}, coords=({latitude},{longitude})")

        if not all([image_url, keyword, latitude, longitude, machine_id, timestamp]):
            logger.error("Missing required fields")
            return jsonify({'error': 'Missing required fields'}), 400

        try:
            readable_time = datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"Timestamp: {readable_time}")
        except:
            readable_time = 'Invalid timestamp'
            logger.warning(f"Invalid timestamp: {timestamp}")

        # 2. Download image
        download_result = download_image(image_url)
        if not download_result["success"]:
            logger.error(f"Image download failed: {download_result['error']}")
            return jsonify({'error': f'Failed to download image. Detail: {download_result["error"]}'}), 400
        image_path = download_result["image_path"]
        logger.info(f"Image downloaded to: {image_path}")

        # 3. Scrape comments if comment_url provided
        matched_keyword = keyword  # Default to provided keyword
        if comment_url:
            comments = fetch_comments(comment_url)
            if comments:
                matched_result = find_best_match(keyword, comments)
                if matched_result:
                    matched_keyword = matched_result
                    logger.info(f"Matched keyword: {matched_keyword}")
                else:
                    logger.warning("No keyword match found in comments, using original keyword")
            else:
                logger.warning("No comments found, using original keyword")

        # 4. Generate AES key
        key = generate_key(latitude, longitude, matched_keyword, machine_id)
        logger.info("Key generated successfully")

        # 5. Extract binary LSB data - IMPROVED EXTRACTION ALGORITHM
        img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            logger.error("Failed to load image")
            return jsonify({'error': 'Failed to load image'}), 400

        # Extract all LSB from the image first
        binary_data = ""
        for row in img:
            for pixel in row:
                for channel in range(min(3, len(pixel))):  # Limit to RGB channels
                    binary_data += str(pixel[channel] & 1)
                    # Check for terminator every 8 bits
                    if len(binary_data) % 8 == 0 and len(binary_data) >= 24:  # Minimum length for '###'
                        # Check if we have the terminator
                        last_chars = ''.join(chr(int(binary_data[i:i+8], 2)) for i in range(len(binary_data)-24, len(binary_data), 8))
                        if '###' in last_chars:
                            logger.info("Found terminator marker in LSB data")
                            break
                if '###' in last_chars:
                    break
            if '###' in last_chars:
                break

        # Convert binary to ASCII
        binary_chars = []
        for i in range(0, len(binary_data), 8):
            if i + 8 <= len(binary_data):
                byte = binary_data[i:i+8]
                binary_chars.append(chr(int(byte, 2)))

        extracted_text = ''.join(binary_chars)
        
        # Find the terminator and extract the base64 data
        if '###' not in extracted_text:
            # Try a different approach - get all binary data and search
            logger.warning("Terminator not found in initial extraction, trying full image scan")
            binary_data = ""
            for row in img:
                for pixel in row:
                    for channel in range(min(3, len(pixel))):
                        binary_data += str(pixel[channel] & 1)
            
            # Build string from all binary data
            all_chars = []
            for i in range(0, len(binary_data), 8):
                if i + 8 <= len(binary_data):
                    byte = binary_data[i:i+8]
                    all_chars.append(chr(int(byte, 2)))
            
            full_text = ''.join(all_chars)
            if '###' in full_text:
                extracted_text = full_text
                logger.info("Found terminator in full image scan")
            else:
                logger.error("Terminator ### not found even in full image scan")
                return jsonify({'error': 'Invalid hidden data format - no terminator found'}), 400

        # Extract the base64 data
        base64_data = extracted_text.split('###')[0]
        logger.info(f"Extracted base64 data of length: {len(base64_data)}")

        # 7. Clean and decode base64/JSON
        clean_base64 = re.sub(r'[^A-Za-z0-9+/=]', '', base64_data)
        try:
            decoded_json = base64.b64decode(clean_base64).decode('utf-8')
            decoded_data = json.loads(decoded_json)
            logger.info("Successfully decoded JSON data")
        except Exception as e:
            logger.error(f"Base64 or JSON decode error: {str(e)}")
            logger.error(f"First 50 chars of clean_base64: {clean_base64[:50]}...")
            return jsonify({'error': f'Base64 or JSON decoding failed: {str(e)}'}), 400

        # 8. Extract fields
        try:
            iv = base64.b64decode(decoded_data['iv'])
            tag = base64.b64decode(decoded_data['tag'])
            encrypted_message = base64.b64decode(decoded_data['msg'])
            start_timestamp = decoded_data['start_timestamp']
            end_timestamp = decoded_data['end_timestamp']
            ttl = decoded_data['ttl']
            logger.info(f"Extracted timestamp window: {start_timestamp} to {end_timestamp}")
        except KeyError as e:
            logger.error(f"Missing key in decoded data: {str(e)}")
            return jsonify({'error': f'Missing required field in hidden data: {str(e)}'}), 400

        # 9. Validate timestamp
        current_time = int(time.time())
        if not (start_timestamp <= current_time <= end_timestamp):
            logger.warning(f"Decryption attempt outside allowed window: {current_time} not in [{start_timestamp}, {end_timestamp}]")
            return jsonify({"error": "Session Expired: The current time is outside the allowed window."}), 403

        # 10. AES-GCM decrypt
        if any(x is None for x in [key, iv, tag, encrypted_message]):
            logger.error("Missing AES-GCM parameters")
            return jsonify({'error': 'Invalid decryption data - missing parameters'}), 400

        try:
            cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted_message = decryptor.update(encrypted_message) + decryptor.finalize()
            final_message = decrypted_message.decode()
            logger.info("Decryption successful")
        except Exception as e:
            logger.error(f"Decryption error: {str(e)}")
            return jsonify({'error': f'Decryption failed: {str(e)}'}), 400

        # 11. Cleanup
        try:
            os.remove(image_path)
            logger.info(f"Cleaned up temporary file: {image_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up temp file: {str(e)}")

        # 12. Return message
        return jsonify({"message": final_message})

    except Exception as e:
        import traceback
        logger.error("Unhandled exception occurred")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Decryption failed: {str(e)}'}), 500
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
