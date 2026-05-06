import os
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth  # import OAuth here

# ======================================================
# 🌍 Load Environment Variables
# ======================================================
load_dotenv()

# ======================================================
# 🔹 Initialize OAuth (single instance)
# ======================================================
oauth = OAuth()  # single app-wide instance

# ======================================================
# 🔹 Import Blueprints
# ======================================================
from .routes import api as api_bp
from .auth import auth_bp
from .routes_chatbot import chatbot_bp  # ✅ Correct file name

# ======================================================
# 🧩 Flask App Factory
# ======================================================
def create_app():
    app = Flask(__name__)

    # --------------------------------------------------
    # Secret key for sessions (required for OAuth + CSRF)
    # Must be set BEFORE initializing OAuth
    # --------------------------------------------------
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "super-secret-session-key")

    # --------------------------------------------------
    # CORS Configuration
    # --------------------------------------------------
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

    # --------------------------------------------------
    # JWT Configuration
    # --------------------------------------------------
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "fallback-secret")
    JWTManager(app)

    # --------------------------------------------------
    # MongoDB Configuration
    # --------------------------------------------------
    app.config["MONGO_URI"] = os.getenv("MONGO_URI")
    if not app.config["MONGO_URI"]:
        print("⚠️ Warning: MONGO_URI not found in .env — MongoDB may not connect properly.")

    # --------------------------------------------------
    # Initialize OAuth with Flask app
    # --------------------------------------------------
    oauth.init_app(app)

    # --------------------------------------------------
    # AI Provider Debug Info
    # --------------------------------------------------
    ai_provider = os.getenv("AI_PROVIDER", "huggingface")
    print(f"\n🤖 Active AI Provider: {ai_provider.upper()}")

    # --------------------------------------------------
    # Register Blueprints — only required routes
    # --------------------------------------------------
    app.register_blueprint(api_bp, url_prefix="/api")          # ML /predict & symptoms
    app.register_blueprint(auth_bp, url_prefix="/auth")        # Signup/Login/Profile
    app.register_blueprint(chatbot_bp, url_prefix="/chatbot")  # Cleaned chatbot routes

    # --------------------------------------------------
    # Debugging — Print All Registered Routes
    # --------------------------------------------------
    print("\n--- Registered Routes ---")
    for rule in app.url_map.iter_rules():
        print(f"{rule}")
    print("-------------------------\n")

    return app
