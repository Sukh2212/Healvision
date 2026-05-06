import os
from flask import Blueprint, request, jsonify, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import certifi

# Import oauth instance initialized in __init__.py
from . import oauth

# -----------------------------
# Blueprint
# -----------------------------
auth_bp = Blueprint("auth", __name__)

# -----------------------------
# MongoDB Atlas connection
# -----------------------------
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI not found in .env file")

try:
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client["healvision"]
    users_collection = db["users"]
except Exception as e:
    raise RuntimeError(f"❌ MongoDB connection failed: {e}")

# -----------------------------
# Google OAuth Configuration (OpenID Connect)
# -----------------------------
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

google = oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# -----------------------------
# Signup Route (Email)
# -----------------------------
@auth_bp.route("/signup", methods=["POST"])
def signup():
    try:
        data = request.json
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")
        age = data.get("age")
        gender = data.get("gender")

        if not name or not email or not password:
            return jsonify({"error": "Name, email, and password are required"}), 400

        if users_collection.find_one({"email": email}):
            return jsonify({"error": "Email already exists"}), 400

        hashed_pw = generate_password_hash(password)
        result = users_collection.insert_one({
            "name": name,
            "email": email,
            "password_hash": hashed_pw,
            "age": age,
            "gender": gender,
            "auth_type": "email",
            "created_at": datetime.utcnow()
        })

        access_token = create_access_token(identity=str(result.inserted_id))
        return jsonify({
            "message": "Signup successful",
            "token": access_token,
            "user": {
                "id": str(result.inserted_id),
                "name": name,
                "email": email,
                "age": age,
                "gender": gender
            }
        }), 201

    except Exception as e:
        print("❌ Signup failed:", e)
        return jsonify({"error": "Signup failed", "details": str(e)}), 500

# -----------------------------
# Login Route (Email)
# -----------------------------
@auth_bp.route("/login", methods=["POST"])
def login():
    try:
        data = request.json
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        user = users_collection.find_one({"email": email})
        if not user or not check_password_hash(user.get("password_hash",""), password):
            return jsonify({"error": "Invalid email or password"}), 401

        access_token = create_access_token(identity=str(user["_id"]))
        return jsonify({
            "message": "Login successful",
            "token": access_token,
            "user": {
                "id": str(user["_id"]),
                "name": user["name"],
                "email": user["email"],
                "age": user.get("age"),
                "gender": user.get("gender")
            }
        }), 200

    except Exception as e:
        print("❌ Login failed:", e)
        return jsonify({"error": "Login failed", "details": str(e)}), 500

# -----------------------------
# Profile Route (Protected)
# -----------------------------
@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
def profile():
    user_id = get_jwt_identity()
    try:
        user = users_collection.find_one({"_id": ObjectId(user_id)}, {"password_hash": 0})
        if not user:
            return jsonify({"error": "User not found"}), 404

        user["_id"] = str(user["_id"])
        return jsonify({"user": user}), 200
    except Exception as e:
        print("❌ Profile fetch failed:", e)
        return jsonify({"error": "Invalid token or user ID", "details": str(e)}), 400

# -----------------------------
# Google Login Route
# -----------------------------
@auth_bp.route("/google")
def google_login():
    redirect_uri = url_for('auth.google_callback', _external=True, _scheme="http")  # localhost testing
    return google.authorize_redirect(redirect_uri)

# -----------------------------
# Google Callback Route (Fixed)
# -----------------------------
@auth_bp.route("/google/callback")
def google_callback():
    try:
        # Exchange code for token
        token = google.authorize_access_token()

        # Parse ID token
        user_info = google.parse_id_token(token, nonce=session.get("oauth_nonce"))

        email = user_info.get('email')
        name = user_info.get('name', '')
        age = None
        gender = None

        # Check if user exists
        user = users_collection.find_one({"email": email})
        if not user:
            new_user = {
                "name": name,
                "email": email,
                "password_hash": None,
                "auth_type": "google",
                "age": age,
                "gender": gender,
                "created_at": datetime.utcnow()
            }
            result = users_collection.insert_one(new_user)
            user_id = str(result.inserted_id)
        else:
            user_id = str(user["_id"])

        # Generate JWT token
        access_token = create_access_token(identity=user_id)

        # Redirect to predict.html with token
        frontend_url = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500/frontend")
        return redirect(f"{frontend_url}/index.html?token={access_token}")  # ✅ Important change

    except Exception as e:
        print("❌ Google login failed:", e)
        return jsonify({"error": "Google login failed", "details": str(e)}), 500

        # Generate JWT token
        access_token = create_access_token(identity=user_id)

        # ✅ Redirect to frontend with token
        frontend_url = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500/frontend")
        return redirect(f"{frontend_url}?token={access_token}")

    except Exception as e:
        print("❌ Google login failed:", e)
        return jsonify({"error": "Google login failed", "details": str(e)}), 500
