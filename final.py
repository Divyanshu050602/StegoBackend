from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# In-memory storage (you can replace this with DB later)
location_store = {}

@app.route('/')
def index():
    return "✅ Backend is running!"


# 1️⃣ Store recipient's geolocation
@app.route('/store-location', methods=['POST'])
def store_location():
    data = request.get_json()
    sender_email = data.get('senderEmail')
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    if not all([sender_email, latitude, longitude]):
        return jsonify({"error": "Missing fields"}), 400

    # Store location keyed by sender's email
    location_store[sender_email] = {
        "latitude": latitude,
        "longitude": longitude
    }

    print(f"Location stored for {sender_email}: {latitude}, {longitude}")
    return jsonify({"message": "Location stored successfully"}), 200


# 2️⃣ Encrypt image using stored location, keyword, and timestamp
@app.route('/encrypt-image', methods=['POST'])
def encrypt_image():
    data = request.form
    sender_email = data.get('senderEmail')
    keyword = data.get('keyword')
    start_timestamp = data.get('startTimestamp')
    end_timestamp = data.get('endTimestamp')
    message = data.get('message')

    image_file = request.files.get('image')

    # Validation
    if not all([sender_email, keyword, start_timestamp, end_timestamp, image_file, message]):
        return jsonify({"error": "Missing fields"}), 400

    if sender_email not in location_store:
        return jsonify({"error": "Location not yet received for this sender"}), 404

    # Retrieve stored location
    location = location_store.get(sender_email)
    latitude = location["latitude"]
    longitude = location["longitude"]

    # Combine all values into encryption key
    encryption_key = f"{keyword}_{start_timestamp}_{end_timestamp}_{latitude}_{longitude}"

    # 🔒 Fake encryption logic (just for demo purposes)
    # Save uploaded image
    save_path = os.path.join("encrypted_images", f"{datetime.now().timestamp()}_encrypted.png")
    os.makedirs("encrypted_images", exist_ok=True)
    image_file.save(save_path)

    # Log
    print("Encryption triggered with:")
    print(f"Message: {message}")
    print(f"Encryption Key: {encryption_key}")
    print(f"Image saved at: {save_path}")

    return jsonify({"message": "Image encrypted", "saved_path": save_path}), 200


# Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

