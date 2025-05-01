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
        # 1. Extract form data
        image_url = request.form.get('image_url')
        comment_url = request.form.get('comment_url')
        keyword = request.form.get('keyword')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        machine_id = request.form.get('machine_id')

        form_data = {
            "image_url": image_url,
            "comment_url": comment_url,
            "keyword": keyword,
            "latitude": latitude,
            "longitude": longitude,
            "machine_id": machine_id
        }

        if not all(form_data.values()):
            return jsonify({'error': 'Missing required fields'}), 400

        # ASCII validation
        for key, value in form_data.items():
            try:
                value.encode('ascii')
            except UnicodeEncodeError:
                return jsonify({'error': f'Invalid input: {key} must contain only ASCII characters'}), 400

        latitude = float(latitude)
        longitude = float(longitude)

        # 2. Download image
        download_result = download_image(image_url)
        if not download_result["success"]:
            return jsonify({'error': f'Failed to download image. Detail: {download_result["error"]}'}), 400
        image_path = download_result["image_path"]

        # 3. Scrape comments
        comments = fetch_comments(comment_url)
        if not comments:
            return jsonify({'error': 'No comments found to match keyword'}), 400

        # 4. NLP keyword match
        matched_keyword = find_best_match(keyword, comments)

        # 5. Generate key
        key = generate_key(latitude, longitude, keyword, machine_id)

        # 6. Read image & extract binary
        img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            return jsonify({'error': 'Failed to load image'}), 400

        binary_data = ""
        for row in img:
            for pixel in row:
                for channel in range(len(pixel)):
                    binary_data += str(pixel[channel] & 1)

        byte_array = bytearray()
        for i in range(0, len(binary_data), 8):
            byte_chunk = binary_data[i:i+8]
            if len(byte_chunk) < 8:
                break
            byte_array.append(int(byte_chunk, 2))

        full_message = byte_array.decode('utf-8', errors='ignore')

        # Extract payload using delimiter
        extracted_payload = full_message.split("###")[0]
        trimmed_payload = extracted_payload.strip()

        # ✅ Fix base64 padding if missing
        missing_padding = len(trimmed_payload) % 4
        if missing_padding:
            trimmed_payload += '=' * (4 - missing_padding)

        try:
            logger.info(f"[DEBUG] Base64 Payload (trimmed): {trimmed_payload[:50]}...")
            decoded_bytes = base64.b64decode(trimmed_payload, validate=True)
            decoded_data = json.loads(decoded_bytes.decode('utf-8'))
        except Exception as e:
            logger.exception("Base64 decoding failed")
            return jsonify({'error': f'Error decoding message: {str(e)}'}), 400

        # 7. Extract encrypted fields
        iv = base64.b64decode(decoded_data['iv'])
        tag = base64.b64decode(decoded_data['tag'])
        encrypted_message = base64.b64decode(decoded_data['msg'])
        start_timestamp = decoded_data['start_timestamp']
        end_timestamp = decoded_data['end_timestamp']
        ttl = decoded_data['ttl']

        # 8. Time check
        current_time = int(time.time())
        if not (start_timestamp <= current_time <= end_timestamp):
            return jsonify({"error": "[ERROR] Session Expired: The current time is outside the allowed window."}), 403

        # 9. Location verification
        decrypted_lat = decrypt_message(decoded_data['lat'], key, decoded_data['iv_loc'], decoded_data['tag_loc'])
        decrypted_lon = decrypt_message(decoded_data['lon'], key, decoded_data['iv_loc'], decoded_data['tag_loc'])

        if decrypted_lat is None or decrypted_lon is None:
            return jsonify({"error": "Failed to decrypt location"}), 400

        if round(float(decrypted_lat), 3) != round(latitude, 3) or round(float(decrypted_lon), 3) != round(longitude, 3):
            return jsonify({'error': 'Location mismatch. Decryption denied.'}), 403

        # 10. Decrypt message
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_message = decryptor.update(encrypted_message) + decryptor.finalize()

        # 11. Cleanup
        os.remove(image_path)

        # 12. Return decrypted message
        return jsonify({
            "message": decrypted_message.decode()
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Decryption failed: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
