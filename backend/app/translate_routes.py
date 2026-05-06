import os
from flask import Blueprint, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from deep_translator import GoogleTranslator   # ✅ Replaced googletrans with deep-translator

# ==========================================================
# 🌍 Load environment variables
# ==========================================================
load_dotenv()

# ==========================================================
# 🌐 Blueprint Setup
# ==========================================================
translate_bp = Blueprint("translate", __name__, url_prefix="/translate")
CORS(translate_bp)

# ==========================================================
# 🔤 Supported Languages
# ==========================================================
SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "pa": "Punjabi",
    "ta": "Tamil"
}

# ==========================================================
# 🌐 Translation Endpoint
# ==========================================================
@translate_bp.route("/text", methods=["POST", "OPTIONS"])
def translate_text():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    data = request.get_json() or {}
    text = data.get("text", "")
    target_lang = data.get("target_lang", "en")

    if not text.strip():
        return jsonify({"error": "No text provided"}), 400

    if target_lang not in SUPPORTED_LANGUAGES:
        return jsonify({"error": f"Unsupported language: {target_lang}"}), 400

    try:
        # ✅ Use Deep Translator
        translated = GoogleTranslator(source="auto", target=target_lang).translate(text)
        return jsonify({
            "original": text,
            "translated": translated,
            "lang": SUPPORTED_LANGUAGES[target_lang]
        })
    except Exception as e:
        print("⚠️ Translation failed:", e)
        return jsonify({"error": "Translation failed", "details": str(e)}), 500
