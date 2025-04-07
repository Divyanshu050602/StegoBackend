import os
import cv2
import numpy as np
import base64
import time
import json
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from hashlib import sha256
from werkzeug.utils import secure_filename

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

def hide_message_in_image(image_path, message, output_path, lat, lon, keyword, machine_id, ttl=DEFAULT_TTL, timestamp=None):
    key = generate_key(lat, lon, keyword, machine_id)
    iv, tag, encrypted_message = encrypt_message(message, key)
    timestamp = timestamp if timestamp else int(time.time())

    # Encrypt lat/lon also
    iv_loc, tag_loc, encrypted_lat = encrypt_message(str(lat), key)
    _, _, encrypted_lon = encrypt_message(str(lon), key)

    data_dict = {
        'iv': base64.b64encode(iv).decode(),
        'tag': base64.b64encode(tag).decode(),
        'msg': encrypted_message,
        'timestamp': timestamp,
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

@app.route("/encrypt", methods=["POST"])
def encrypt_handler():
    try:
        image = request.files['image']
        message = request.form['message']
        keyword = request.form['keyword']
        lat = request.form['latitude']
        lon = request.form['longitude']
        machine_id = request.form['machine_id']
        timestamp = int(request.form.get('timestamp', time.time()))

        filename = secure_filename(image.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        output_path = os.path.join(app.config['ENCRYPTED_FOLDER'], "encrypted_" + filename)

        image.save(input_path)

        hide_message_in_image(
            input_path, message, output_path,
            lat, lon, keyword, machine_id, timestamp=timestamp
        )

        return send_file(output_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/decrypt", methods=["POST"])
def decrypt_handler():
    try:
        image = request.files['image']
        keyword = request.form['keyword']
        lat = request.form['latitude']
        lon = request.form['longitude']
        machine_id = request.form['machine_id']

        key = generate_key(lat, lon, keyword, machine_id)

        input_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(image.filename))
        image.save(input_path)

        # LSB decoding
        img = cv2.imread(input_path, cv2.IMREAD_UNCHANGED)
        binary_data = ""
        for row in img:
            for pixel in row:
                for channel in range(len(pixel)):
                    binary_data += str(pixel[channel] & 1)

        bytes_data = [binary_data[i:i + 8] for i in range(0, len(binary_data), 8)]
        extracted_message = ''.join(chr(int(b, 2)) for b in bytes_data if int(b, 2) != 0)
        extracted_message = extracted_message.split("###")[0]

        decoded_data = json.loads(base64.b64decode(extracted_message).decode())

        iv = base64.b64decode(decoded_data['iv'])
        tag = base64.b64decode(decoded_data['tag'])
        encrypted_message = base64.b64decode(decoded_data['msg'])
        timestamp = decoded_data['timestamp']
        ttl = decoded_data['ttl']

        current_time = int(time.time())
        if current_time > timestamp + ttl:
            return jsonify({"message": "[ERROR] Session Expired: Time limit exceeded."})

        cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_message = decryptor.update(encrypted_message) + decryptor.finalize()

        return jsonify({"message": decrypted_message.decode()})

    except Exception as e:
        return jsonify({"error": f"[ERROR] Decryption failed: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
