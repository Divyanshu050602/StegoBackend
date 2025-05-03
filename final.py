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
import hashlib

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

def truncate_to_3_decimal_places(value):
    return float(str(value).split('.')[0] + '.' + str(value).split('.')[1][:3])

@app.route('/')
def index():
    return "✅ Backend is running!"

def generate_key(lat, lon, keyword, machine_id):
    lat = truncate_to_3_decimal_places(lat)
    lon = truncate_to_3_decimal_places(lon)
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

    lat = truncate_to_3_decimal_places(lat)
    lon = truncate_to_3_decimal_places(lon)

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
        latitude = truncate_to_3_decimal_places(float(data['latitude']))
        longitude = truncate_to_3_decimal_places(float(data['longitude']))
        device_id = data['deviceId']

        print(f"[Location Received] From: {sender_email}, Location: ({latitude}, {longitude}), Device ID: {device_id}")

        # Store only the requir   ed fields
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

        lat = round(float(location_data.get("latitude")), 3)
        lon = round(float(location_data.get("longitude")), 3)
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


@app.route('/decrypt', methods=['POST'])
def decrypt_handler():
    try:
        # 1. Extract data from form
        image_url = request.form.get('image_url')
        comment_url = request.form.get('comment_url')
        keyword = request.form.get('keyword')
        latitude = truncate_to_3_decimal_places(float(request.form.get('latitude')))
        longitude = truncate_to_3_decimal_places(float(request.form.get('longitude')))
        machine_id = request.form.get('machine_id')
        timestamp = request.form.get('timestamp')

        if not all([image_url, comment_url, keyword, latitude, longitude, machine_id, timestamp]):
            return jsonify({'error': 'Missing required fields'}), 400

        keywords = [k.strip() for k in keyword.split(',') if k.strip()]

        try:
            readable_time = datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
        except:
            readable_time = 'Invalid timestamp'

        # 2. Download the image
        download_result = download_image(image_url)
        if not download_result["success"]:
            return jsonify({'error': f'Failed to download image. Detail: {download_result["error"]}'}), 400
        image_path = download_result["image_path"]

        # 3. Scrape comments
        comments = fetch_comments(comment_url)
        if not comments:
            return jsonify({'error': 'No comments found to match keyword'}), 400

        # 4. NLP: Find matched keyword
        matched_keyword = find_best_match(keywords, comments)

        # 5. Generate decryption key
        key = generate_key(latitude, longitude, matched_keyword, machine_id)

        # 6. Decode LSB message from image
        img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            return jsonify({'error': 'Failed to load image'}), 400

        bits=[]
        for row in img:
            for pixel in row:
                for channel in range(len(pixel)):
                    bits.append(str(pixel[channel] & 1))

        binary_data = ''.join(bits)
        bytes_data = [binary_data[i:i + 8] for i in range(0, len(binary_data), 8)]
        extracted_message = ''.join(chr(int(b, 2)) for b in bytes_data if int(b, 2) != 0)
        extracted_message = extracted_message.split("###")[0]


        # 🔍 Log the raw extracted message (for debugging)
        message_digest = hashlib.sha256(extracted_message.encode('utf-8')).hexdigest()
        print(f"[DEBUG] Message length (chars): {len(extracted_message)}")
        print(f"[DEBUG] Contains delimiter ###: {'###' in extracted_message}")

     
        try:
            decoded_data = json.loads(base64.b64decode(extracted_message).decode())
        except Exception as e:
            return jsonify({'error': f'Error decoding base64 message: {str(e)}'}), 400

        # 7. Extract encryption fields
        iv = base64.b64decode(decoded_data['iv'])
        tag = base64.b64decode(decoded_data['tag'])
        encrypted_message = base64.b64decode(decoded_data['msg'])
        start_timestamp = decoded_data['start_timestamp']
        end_timestamp = decoded_data['end_timestamp']
        ttl = decoded_data['ttl']

        current_time = int(time.time())
        if not (start_timestamp <= current_time <= end_timestamp):
            return jsonify({"error": "[ERROR] Session Expired: The current time is outside the allowed window."}), 403

        # 8. Decrypt AES-GCM
        if any(x is None for x in [key, iv, tag, encrypted_message]):
            return jsonify({'error': 'Invalid decryption data'}), 400

        cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_message = decryptor.update(encrypted_message) + decryptor.finalize()

        # 9. Log internally
        decryption_logs=[]
        decryption_logs.append({
            'image_url': image_url,
            'keyword': keyword,
            'latitude': latitude,
            'longitude': longitude,
            'timestamp': timestamp,
            'readable_time': readable_time,
            'machine_id': machine_id,
            'message': decrypted_message.decode(),
            'comments': comments,
            'matched_keyword': matched_keyword
        })

        # 10. Cleanup
        os.remove(image_path)

        # 11. Return decrypted result
        return jsonify({
            "message": decrypted_message.decode()
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Decryption failed: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
