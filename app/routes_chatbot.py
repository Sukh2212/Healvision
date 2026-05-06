import os
import json
from flask import Blueprint, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import random
import re


# ==========================================================
# 🌍 Load environment variables
# ==========================================================
load_dotenv()

# ==========================================================
# 🧩 Blueprint
# ==========================================================
chatbot_bp = Blueprint("chatbot", __name__, url_prefix="/chatbot")
CORS(chatbot_bp)

# ==========================================================
# 🤖 AI Provider Setup (Hugging Face active)
# ==========================================================
AI_PROVIDER = os.getenv("AI_PROVIDER", "huggingface").lower()
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
HUGGINGFACE_MODEL = os.getenv("HUGGINGFACE_MODEL", "meta-llama/Llama-3.1-8B-Instruct")

# ==========================================================
# 📘 Knowledge Base Loader
# ==========================================================
BASE_DIR = os.path.dirname(__file__)
KNOWLEDGE_PATH = os.path.join(BASE_DIR, "disease_knowledge.json")

def load_knowledge():
    path_to_use = KNOWLEDGE_PATH
    fallback_path = os.path.join(BASE_DIR, "..", "app", "disease_knowledge.json")
    if not os.path.exists(KNOWLEDGE_PATH) and os.path.exists(fallback_path):
        path_to_use = fallback_path
    with open(path_to_use, "r", encoding="utf-8") as f:
        kb = json.load(f)
    if isinstance(kb, list):
        kb_dict = {item.get("name", "").lower(): item for item in kb}
    elif isinstance(kb, dict):
        kb_dict = {k.lower(): v for k, v in kb.items()}
    else:
        kb_dict = {}
    return kb_dict

knowledge = load_knowledge()

# ==========================================================
# 🧠 Unified AI Chat Function (Hugging Face OpenAI-style)
# ==========================================================
def generate_ai_reply(prompt, mode="general"):
    used_provider = None
    try:
        if not HUGGINGFACE_API_KEY:
            return {"text": "⚠️ HF_TOKEN not found in environment variables.", "provider": None}

        from openai import OpenAI

        client = OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=HUGGINGFACE_API_KEY,
        )

        completion = client.chat.completions.create(
            model=HUGGINGFACE_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )


        # completion = client.chat.completions.create(
        #     model=f"{HUGGINGFACE_MODEL}:fireworks-ai",
        #     messages=[{"role": "user", "content": prompt}],
        # )

        text = completion.choices[0].message.content
        used_provider = "Hugging Face Llama 3.1"
        return {"text": text, "provider": used_provider}

    except Exception as e:
        print("💥 Error while generating text:", e)
        return {"text": f"⚠️ Error while generating text: {e}", "provider": None}
    
def extract_disease_from_message(msg):
    msg_clean = msg.lower().strip()

    # Try direct match
    if msg_clean in knowledge:
        return msg_clean

    # Try checking each disease inside the sentence
    for disease in knowledge.keys():
        if disease in msg_clean:
            return disease

    return None        

# ==========================================================
# 1️⃣ General Medical Q&A (AI-powered)
# ==========================================================
@chatbot_bp.route("/chat/ai", methods=["POST", "OPTIONS"])
def ai_chat():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.json
    user_message = data.get("message", "")
    reply = generate_ai_reply(user_message, mode="ai")
    return jsonify({"mode": "ai", "reply": reply})

# ==========================================================
# 2️⃣ Diet & Lifestyle Recommendations (Hybrid)
# ==========================================================
@chatbot_bp.route("/chat/diet", methods=["POST", "OPTIONS"])
def diet_chat():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    
    data = request.json
    user_message = data.get("message", "").strip().lower()

    # -------------------------
    # Extract disease using helper function
    # -------------------------
    disease_from_sentence = extract_disease_from_message(user_message)

    if disease_from_sentence:
        user_message_clean = disease_from_sentence
    else:
        user_message_clean = user_message

    # -------------------------
    # Try matching in knowledge base
    # -------------------------
    matched = knowledge.get(user_message_clean)

    if not matched:
        disease_key = user_message_clean.replace("(", "").replace(")", "").replace("-", "").replace(" ", "")
        matched = next(
            (v for k, v in knowledge.items() if disease_key in k.replace(" ", "")), 
            None
        )

    # -------------------------
    # If found in knowledge base (ML)
    # -------------------------
    if matched and (matched.get("diet") or matched.get("workout")):
        return jsonify({
            "mode": "diet",
            "reply": {
                "diet": matched.get("diet", []),
                "workout": matched.get("workout", [])
            }
        })

    # -------------------------
    # AI fallback
    # -------------------------
    prompt = f"Provide safe diet and lifestyle recommendations for: {user_message}. Avoid prescriptions."
    ai_reply = generate_ai_reply(prompt, mode="diet")

    return jsonify({
        "mode": "diet",
        "reply": {
            "diet": ai_reply.get("text", ""),
            "workout": []
        }
    })



# ==========================================================
# 3️⃣ Emergency Guidance Detection (Enhanced v3 — Regex + Normalization + Readable Labels)
# ==========================================================
@chatbot_bp.route("/chat/emergency", methods=["POST", "OPTIONS"])
def emergency_check():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    import re

    data = request.get_json()
    message = data.get("message", "").lower()

    # ✅ Step 1: Normalize input (remove punctuation, extra spaces, etc.)
    message = re.sub(r'[^a-z\s]', ' ', message)
    message = re.sub(r'\s+', ' ', message).strip()

    # ✅ Step 2: Regex patterns (robust & typo-tolerant)
    emergency_patterns = {
        r'chest\s*pain|chestpain|pain\s*in\s*chest|heart\s*attack|heart\s*problem|heart\s*issue|heart\s*ache|heart\s*trouble':
            "🚨 Heart-related emergency. Call emergency services immediately.",
        r'(difficulty|trouble)\s*breathing|shortness\s*of\s*breath|cant\s*breathe|cannot\s*breathe|unable\s*to\s*breathe':
            "😮‍💨 Breathing difficulty detected. Seek emergency help immediately.",
        r'severe\s*bleeding|heavy\s*bleeding|bleed\s*a\s*lot|bleeding\s*badly':
            "🩸 Severe bleeding detected. Apply pressure and seek emergency care.",
        r'loss\s*of\s*consciousness|unconscious|fainted|passed\s*out':
            "😴 Unconsciousness detected. Check pulse, start CPR if needed, call for help.",
        r'stroke|paralysis|half\s*body\s*paralyzed|face\s*drooping|slurred\s*speech':
            "🧠 Possible stroke! Call emergency immediately.",
        r'seizure|convulsion|fits|epilepsy':
            "⚡ Seizure detected. Keep the person safe, call emergency help.",
        r'suicidal|suicide|kill\s*myself|want\s*to\s*die|ending\s*my\s*life':
            "🆘 Suicidal thoughts detected. Please reach out for immediate help or call local helplines.",
        r'severe\s*burn|bad\s*burn|chemical\s*burn|electric\s*burn':
            "🔥 Severe burn detected. Cool the area and seek emergency care.",
        r'accident|major\s*injury|severe\s*injury|fracture|broken\s*bone':
            "🚑 Major accident or injury detected. Seek emergency medical attention.",
        r'severe\s*abdominal\s*pain|stomach\s*pain|abdominal\s*cramps':
            "🤕 Severe abdominal pain detected. Visit emergency care.",
        r'severe\s*headache|migraine\s*attack|head\s*pain\s*severe':
            "💢 Severe headache detected. If persistent, seek emergency help.",
        r'high\s*fever|very\s*high\s*temperature|uncontrolled\s*fever':
            "🌡️ High fever detected. Seek medical care if it persists."
    }

    # ✅ Step 3: Detect emergencies
    detected_emergencies = []
    for pattern, response in emergency_patterns.items():
        if re.search(pattern, message):
            detected_emergencies.append((pattern, response))

    # ✅ Step 4: Respond based on detection
    if detected_emergencies:
        primary_response = detected_emergencies[0][1]

        # Convert regex patterns to friendly labels
        detected_labels = []
        for pattern, _ in detected_emergencies:
            if "chest" in pattern or "heart" in pattern:
                detected_labels.append("chest pain / heart-related issue")
            elif "breath" in pattern:
                detected_labels.append("breathing problem")
            elif "bleed" in pattern:
                detected_labels.append("severe bleeding")
            elif "unconscious" in pattern or "faint" in pattern:
                detected_labels.append("unconsciousness")
            elif "stroke" in pattern or "paralysis" in pattern:
                detected_labels.append("stroke")
            elif "seizure" in pattern:
                detected_labels.append("seizure")
            elif "suicid" in pattern:
                detected_labels.append("suicidal risk")
            elif "burn" in pattern:
                detected_labels.append("burn injury")
            elif "accident" in pattern or "fracture" in pattern:
                detected_labels.append("major accident or injury")
            elif "abdominal" in pattern or "stomach" in pattern:
                detected_labels.append("severe abdominal pain")
            elif "headache" in pattern:
                detected_labels.append("severe headache")
            elif "fever" in pattern:
                detected_labels.append("high fever")
            else:
                detected_labels.append("emergency condition")

        return jsonify({
            "mode": "emergency",
            "reply": {
                "provider": "HealVision AI",
                "text": f"{primary_response} (Detected: {', '.join(set(detected_labels))})"
            }
        })

    # ✅ No emergency found
    else:
        return jsonify({
            "mode": "general",
            "reply": {
                "provider": "HealVision AI",
                "text": "✅ No emergency detected. Continue monitoring your condition."
            }
        })



# ==========================================================
# 4️⃣ Daily Health Tips
# ==========================================================
DAILY_TIPS = [
    "Drink at least 8 glasses of water daily.",
    "Take a 30-minute walk every day for better circulation.",
    "Include fresh fruits and vegetables in your diet.",
    "Ensure 7–8 hours of sleep every night.",
    "Practice deep breathing exercises to reduce stress."
]

@chatbot_bp.route("/chat/tips", methods=["POST", "OPTIONS"])  # POST fixed
def daily_tips():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    tips = random.sample(DAILY_TIPS, k=2)
    return jsonify({"mode": "tips", "reply": {"tips": tips}})

# ==========================================================
# 5️⃣ Unified /ask Endpoint
# ==========================================================
@chatbot_bp.route("/ask", methods=["POST", "OPTIONS"])
def unified_chat():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.json
    mode = data.get("mode", "ai").lower()
    message = data.get("message", "")
    reply = {}

    if mode == "ai":
        reply = generate_ai_reply(message, mode="ai")
    elif mode == "diet":
        disease = data.get("disease", "").strip().lower()
        disease_key = disease.replace("(", "").replace(")", "").replace("-", "").replace(" ", "")
        matched = next((v for k, v in knowledge.items() if disease_key in k.replace(" ", "")), None)
        if matched and (matched.get("diet") or matched.get("workout")):
            reply = {"diet": matched.get("diet", []), "workout": matched.get("workout", [])}
        else:
            prompt = f"Provide safe diet and lifestyle recommendations for the disease: {disease}. Avoid prescriptions and ensure general health advice."
            ai_reply = generate_ai_reply(prompt, mode="diet")
            reply = {"diet": ai_reply.get("text", ""), "workout": []}
    elif mode == "emergency":
        emergencies = ["chest pain", "stroke", "unconscious", "difficulty breathing", "severe bleeding", "sudden weakness"]
        is_urgent = any(term in message.lower() for term in emergencies)
        reply = {"urgent": is_urgent}
        reply["message"] = "⚠️ This may be an emergency. Please seek immediate medical care." if is_urgent else "✅ No emergency detected."
    elif mode == "tips":
        tips = random.sample(DAILY_TIPS, k=2)
        reply = {"tips": tips}
    else:
        reply = {"message": "Invalid mode specified."}

    return jsonify({"mode": mode, "reply": reply})
