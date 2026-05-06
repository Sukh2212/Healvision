import json
import os
import certifi
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_cors import CORS
from datetime import datetime
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv

from app.model import (
    model,
    label_encoder,
    get_all_symptoms,
    predict_disease_with_proba,
)

# -----------------------------
# Load environment variables
# -----------------------------
load_dotenv()

# -----------------------------
# Blueprint
# -----------------------------
api = Blueprint("routes", __name__)
CORS(api)  # Enable CORS for all routes

# -----------------------------
# MongoDB Setup
# -----------------------------
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI not found in .env file")

try:
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client["healvision"]
    history_collection = db["prediction_history"]
    users_collection = db["users"]
except Exception as e:
    raise RuntimeError(f"❌ MongoDB connection failed: {e}")

# -----------------------------
# Load knowledge base
# -----------------------------
knowledge_path = os.path.join(os.path.dirname(__file__), "disease_knowledge.json")
if not os.path.exists(knowledge_path):
    knowledge_path = os.path.join(os.path.dirname(__file__), "..", "app", "disease_knowledge.json")

with open(knowledge_path, "r", encoding="utf-8") as f:
    knowledge_base = json.load(f)

# -----------------------------
# Utility functions
# -----------------------------
def get_all_diseases():
    return sorted(list(knowledge_base.keys()))

def get_info(disease: str):
    if not disease:
        return None
    for k in knowledge_base.keys():
        if k.lower() == disease.lower():
            return knowledge_base[k]
    return None

def clean_list(val):
    result = []
    if isinstance(val, list):
        for item in val:
            if isinstance(item, str):
                s = item.strip()
                if s and not s.isdigit():
                    result.append(s.strip("[]'\" "))
    elif isinstance(val, str):
        s = val.strip()
        if s and not s.isdigit():
            result.append(s.strip("[]'\" "))
    return result

def is_valid_objectid(val):
    try:
        ObjectId(str(val))
        return True
    except:
        return False

# -----------------------------
# Symptoms / Diseases / Info
# -----------------------------
@api.route("/symptoms", methods=["GET"])
def symptoms():
    all_symptoms = sorted({sym for kb in knowledge_base.values() for sym in kb.get("symptoms", [])})
    return jsonify({"symptoms": all_symptoms})

@api.route("/diseases", methods=["GET"])
def diseases():
    return jsonify({"diseases": get_all_diseases()})

@api.route("/info", methods=["GET"])
def info():
    disease = request.args.get("disease", "").strip()
    data = get_info(disease)
    if not data:
        return jsonify({"error": f"No info found for '{disease}'"}), 404
    return jsonify({"disease": disease, "data": data})

# -----------------------------
# Predict
# -----------------------------
@api.route("/predict", methods=["POST", "OPTIONS"])
def predict():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    data = request.get_json() or {}

    # -------------------
    # Patient info
    # -------------------
    patient = data.get("patient", {}) or {}
    patient_name = patient.get("name", "").strip()
    patient_age = str(patient.get("age", "")).strip() if isinstance(patient.get("age"), (int, str)) else "N/A"
    patient_gender = patient.get("gender", "").strip()
    patient_history = patient.get("history", "").strip()

    symptoms_dict = data.get("symptoms", {}) or {}
    active_symptoms = [s for s, v in symptoms_dict.items() if v == 1]

    if len(active_symptoms) < 2:
        return jsonify({
            "error": "Please provide at least 2 symptoms for a reliable prediction.",
            "input_symptoms": active_symptoms
        }), 400

    predictions = []

    # -------------------
    # ML Prediction
    # -------------------
    try:
        if model is not None and label_encoder is not None:
            label, confidence, top_prediction = predict_disease_with_proba(symptoms_dict)
            if top_prediction:
                disease = top_prediction[0]["disease"]
                prob = top_prediction[0]["prob"]
                info = knowledge_base.get(disease, {})

                predictions.append({
                    "disease": disease,
                    "confidence": round(prob, 2),
                    "description": info.get("description", ""),  # ✅ Added here
                    "medicines": clean_list(info.get("medicines", [])),
                    "precautions": clean_list(info.get("precautions", [])),
                    "diet": clean_list(info.get("diet", [])),
                    "workout": clean_list(info.get("workout", []))
                })
    except Exception as e:
        print("⚠️ ML prediction failed, falling back to KB:", e)

    # -------------------
    # Knowledge Base fallback
    # -------------------
    if not predictions:
        best_match = None
        best_score = 0
        for disease_name, info in knowledge_base.items():
            kb_symptoms = info.get("symptoms", [])
            matched_count = len(set(active_symptoms).intersection(set(kb_symptoms)))
            score = matched_count / max(len(kb_symptoms), 1)
            if score > best_score:
                best_score = score
                best_match = (disease_name, info)

        if best_match and best_score > 0:
            disease_name, info = best_match
            predictions.append({
                "disease": disease_name,
                "confidence": round(best_score * 100, 2),
                "description": info.get("description", ""),  # ✅ Added here too
                "medicines": clean_list(info.get("medicines", [])),
                "precautions": clean_list(info.get("precautions", [])),
                "diet": clean_list(info.get("diet", [])),
                "workout": clean_list(info.get("workout", []))
            })
        else:
            return jsonify({
                "message": "No match found. Please add more symptoms.",
                "input_symptoms": active_symptoms
            }), 200

    # -------------------
    # ✅ Save history in MongoDB Atlas
    # -------------------
    saved_history = None
    user_id = data.get("user_id")

    try:
        prediction = predictions[0]
        history_doc = {
            "user_id": ObjectId(user_id) if user_id and is_valid_objectid(user_id) else None,
            "name": patient_name or "Unknown",
            "age": patient_age or "N/A",
            "gender": patient_gender or "N/A",
            "history": patient_history or "—",
            "disease": prediction["disease"],
            "confidence": prediction.get("confidence", 0),
            "description": prediction.get("description", ""),  # ✅ Stored in history as well
            "medicines": prediction.get("medicines", []),
            "precautions": prediction.get("precautions", []),
            "diet": prediction.get("diet", []),
            "workout": prediction.get("workout", []),
            "input_symptoms": active_symptoms,
            "timestamp": datetime.utcnow()
        }

        insert_result = history_collection.insert_one(history_doc)
        print(f"✅ History saved for user {user_id}: {insert_result.inserted_id}")
        history_doc["_id"] = str(insert_result.inserted_id)
        history_doc["timestamp"] = history_doc["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        saved_history = history_doc
    except Exception as e:
        print("⚠️ Could not save history:", e)

    # -------------------
    # Return response
    # -------------------
    return jsonify({
        "patient": {
            "name": patient_name,
            "age": patient_age,
            "gender": patient_gender,
            "history": patient_history,
        },
        "input_symptoms": active_symptoms,
        "predictions": predictions,
        "history_saved": bool(saved_history),
        "current_history": saved_history
    })

# -----------------------------
# Prediction History (JWT & Public)
# -----------------------------
@api.route("/history", methods=["GET"])
@jwt_required()
def get_history():
    user_id = get_jwt_identity()
    return _fetch_history(user_id)

@api.route("/history/<string:user_id>", methods=["GET"])
def get_history_by_id(user_id):
    """Public route for frontend popup (after prediction)"""
    return _fetch_history(user_id)

def _fetch_history(user_id):
    """Helper to fetch all user prediction history"""
    if not is_valid_objectid(user_id):
        return jsonify({"error": "Invalid user ID"}), 400
    try:
        records = history_collection.find({"user_id": ObjectId(user_id)}).sort("timestamp", -1)
        result = []
        for record in records:
            ts = record.get("timestamp")
            if ts is None:
                ts_str = "N/A"
            elif isinstance(ts, datetime):
                ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
            else:
                try:
                    ts_str = str(ts)
                except:
                    ts_str = "N/A"

            result.append({
                "id": str(record.get("_id", "")),
                "name": record.get("name", "Unknown"),
                "age": record.get("age", "—"),
                "gender": record.get("gender", "—"),
                "history": record.get("history", "—"),
                "disease": record.get("disease", "Unknown"),
                "confidence": record.get("confidence", 0),
                "description": record.get("description", ""),  # ✅ Added to history response
                "medicines": record.get("medicines", []),
                "precautions": record.get("precautions", []),
                "diet": record.get("diet", []),
                "workout": record.get("workout", []),
                "input_symptoms": record.get("input_symptoms", []),
                "timestamp": ts_str
            })
        return jsonify({"history": result})
    except Exception as e:
        print("❌ Fetch history failed:", e)
        return jsonify({"error": "Failed to fetch history", "details": str(e)}), 500
