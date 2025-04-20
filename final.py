import os
import cv2
import numpy as np
import base64
import time
import json
import traceback
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from hashlib import sha256
from werkzeug.utils import secure_filename
from download_image import download_image
from scrape_comments import fetch_comments
from NLP_comment_and_keyword_analyser import find_best_match

# Constants
DEFAULT_TTL = 600  # 10 minutes
UPLOAD_FOLDER = 'uploads'
ENCRYPTED_FOLDER = 'encrypted'
decryption_logs = []

app = Flask(__name__)
CORS(app)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ENCRYPTED_FOLDER'] = ENCRYPTED_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ENCRYPTED_FOLDER, exist_ok=True)

def log_error(context, e):
    print(f"[ERROR] {context}: {str(e)}")
    print(traceback.format_exc())

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

# Other functions remain the same...

@app.route("/encrypt", methods=["POST"])
def encrypt_handler():
    try:
        image = request.files['image']
        message = request.form['message']
        keyword = request.form['keyword']
        start_timestamp_str = request.form['startTimestamp']
        end_timestamp_str = request.form['endTimestamp']

        try:
            start_dt = datetime.strptime(start_timestamp_str, "%Y-%m-%dT%H:%M")
            end_dt = datetime.strptime(end_timestamp_str, "%Y-%m-%dT%H:%M")
            start_timestamp = int(start_dt.timestamp())
            end_timestamp = int(end_dt.timestamp())
        except Exception as e:
            log_error("Timestamp Parsing", e)
            return jsonify({"error": "Invalid timestamp format"}), 400

        try:
            with open("location_temp.json", "r") as f:
                location_data = json.load(f)
            lat = location_data.get("latitude")
            lon = location_data.get("longitude")
            machine_id = location_data.get("device_id")
        except Exception as e:
            log_error("Loading location_temp.json", e)
            return jsonify({"error": "Location or device data unavailable"}), 400

        if not all([lat, lon, machine_id]):
            return jsonify({"error": "Missing geolocation or device data. Please click the tracking link again."}), 400

        filename = secure_filename(image.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        encrypted_filename = "encrypted_" + os.path.splitext(filename)[0] + ".png"
        output_path = os.path.join(app.config['ENCRYPTED_FOLDER'], encrypted_filename)

        image.save(input_path)

        try:
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
        except Exception as e:
            log_error("Hiding message in image", e)
            return jsonify({"error": f"Encryption failed: {str(e)}"}), 500

        return send_file(
            output_path,
            mimetype='image/png',
            as_attachment=True,
            download_name=encrypted_filename
        )

    except Exception as e:
        log_error("/encrypt", e)
        return jsonify({"error": str(e)}), 500

@app.route('/decrypt', methods=['POST'])
def decrypt_handler():
    try:
        image_url = request.form.get('image_url')
        keyword = request.form.get('keyword')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        machine_id = request.form.get('machine_id')
        timestamp = request.form.get('timestamp')

        if not all([image_url, keyword, latitude, longitude, machine_id, timestamp]):
            return jsonify({'error': 'Missing required fields'}), 400

        try:
            readable_time = datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            log_error("Timestamp parsing", e)
            readable_time = 'Invalid timestamp'

        download_result = download_image(image_url)
        if not download_result["success"]:
            return jsonify({'error': f'Failed to download image. Detail: {download_result["error"]}'}), 400
        image_path = download_result["image_path"]

        comments = get_comments_html(image_url)
        if not comments:
            return jsonify({'error': 'No comments found to match keyword'}), 400

        try:
            matched_keyword = find_best_match(keyword, comments)
        except Exception as e:
            log_error("NLP keyword matching", e)
            matched_keyword = keyword

        key = generate_key(latitude, longitude, keyword, machine_id)

        try:
            img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
            if img is None:
                raise ValueError("Failed to load image")
        except Exception as e:
            log_error("Reading image", e)
            return jsonify({'error': 'Failed to read image'}), 400

        try:
            binary_data = ""
            for row in img:
                for pixel in row:
                    for channel in range(len(pixel)):
                        binary_data += str(pixel[channel] & 1)

            bytes_data = [binary_data[i:i + 8] for i in range(0, len(binary_data), 8)]
            extracted_message = ''.join(chr(int(b, 2)) for b in bytes_data if int(b, 2) != 0)
            extracted_message = extracted_message.split("###")[0]
            decoded_data = json.loads(base64.b64decode(extracted_message).decode())
        except Exception as e:
            log_error("Extracting & decoding hidden message", e)
            return jsonify({'error': f'Decoding failed: {str(e)}'}), 400

        try:
            iv = base64.b64decode(decoded_data['iv'])
            tag = base64.b64decode(decoded_data['tag'])
            encrypted_message = base64.b64decode(decoded_data['msg'])
            start_timestamp = decoded_data['start_timestamp']
            end_timestamp = decoded_data['end_timestamp']
            ttl = decoded_data['ttl']

            current_time = int(time.time())
            if not (start_timestamp <= current_time <= end_timestamp):
                return jsonify({"error": "[ERROR] Session Expired: Time window invalid."}), 403

            cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted_message = decryptor.update(encrypted_message) + decryptor.finalize()
        except Exception as e:
            log_error("Decryption", e)
            return jsonify({'error': f'Decryption failed: {str(e)}'}), 400

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

        os.remove(image_path)

        return jsonify({"message": decrypted_message.decode()})

    except Exception as e:
        log_error("/decrypt", e)
        return jsonify({'error': f'Decryption failed: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
