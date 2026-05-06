# backend/model.py
import os
import joblib
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split, StratifiedKFold, GridSearchCV
from sklearn.metrics import accuracy_score, confusion_matrix
from xgboost import XGBClassifier

# -----------------------------
# Paths
# -----------------------------
BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE_DIR, "models", "disease_model.pkl")
ENCODER_PATH = os.path.join(BASE_DIR, "models", "label_encoder.pkl")
DATASET_PATH = os.path.join(BASE_DIR, "..", "datasets", "Final_Training.csv")
SYMPTOM_LIST_PATH = os.path.join(BASE_DIR, "..", "datasets", "symptoms_list.txt")

# Normalize paths
DATASET_PATH = os.path.abspath(DATASET_PATH)
SYMPTOM_LIST_PATH = os.path.abspath(SYMPTOM_LIST_PATH)
MODEL_PATH = os.path.abspath(MODEL_PATH)
ENCODER_PATH = os.path.abspath(ENCODER_PATH)

# -----------------------------
# Load dataset + symptom columns
# -----------------------------
training_data = pd.read_csv(DATASET_PATH)

# Drop diseases with ≤1 sample
counts = training_data["diseases"].value_counts()
rare_diseases = counts[counts <= 1].index.tolist()
training_data = training_data[training_data["diseases"].isin(counts[counts > 1].index)]

print(f"⚠️ Dropped {len(rare_diseases)} diseases with only 1 sample: {', '.join(rare_diseases)}")
remaining_diseases = training_data["diseases"].nunique()
print(f"✅ Remaining diseases for training: {remaining_diseases}")

symptom_columns = training_data.drop(columns=["diseases"]).columns.tolist()

# Always overwrite symptom list file
os.makedirs(os.path.dirname(SYMPTOM_LIST_PATH), exist_ok=True)
with open(SYMPTOM_LIST_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(symptom_columns))

# =====================================================
# ML Model Training & Persistence
# =====================================================
def train_and_save_model():
    """Train the XGBoost model and save artifacts."""
    df = pd.read_csv(DATASET_PATH)

    # Drop rare diseases
    counts = df["diseases"].value_counts()
    df = df[df["diseases"].isin(counts[counts > 1].index)]

    X = df[symptom_columns]
    y = df["diseases"]

    # Encode labels
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)

    # Sample weights for rare classes
    class_counts = np.bincount(y_encoded)
    inv_freq = {cls: 1.0 / count for cls, count in enumerate(class_counts) if count > 0}
    sample_weights = np.array([inv_freq[label] for label in y_encoded])

    # Stratified split
    X_train, X_test, y_train, y_test, sw_train, sw_test = train_test_split(
        X, y_encoded, sample_weights, test_size=0.2, random_state=42, stratify=y_encoded
    )

    # Save splits for reference
    train_split = X_train.copy()
    train_split["diseases"] = label_encoder.inverse_transform(y_train)
    train_split.to_csv(os.path.join(os.path.dirname(DATASET_PATH), "Training_split.csv"), index=False)

    test_split = X_test.copy()
    test_split["diseases"] = label_encoder.inverse_transform(y_test)
    test_split.to_csv(os.path.join(os.path.dirname(DATASET_PATH), "Testing_split.csv"), index=False)

    # XGBoost classifier
    xgb = XGBClassifier(
        objective="multi:softprob",
        eval_metric="mlogloss",
        use_label_encoder=False,
        random_state=42,
        n_jobs=-1
    )

    param_grid = {
        "n_estimators": [200, 300],
        "max_depth": [4, 6],
        "learning_rate": [0.05, 0.1],
        "subsample": [0.8, 1.0],
        "colsample_bytree": [0.8, 1.0],
        "min_child_weight": [1, 3],
        "reg_alpha": [0, 0.5],
        "reg_lambda": [1, 2]
    }

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    grid = GridSearchCV(
        estimator=xgb,
        param_grid=param_grid,
        scoring="accuracy",
        cv=cv,
        verbose=1,
        n_jobs=-1
    )

    grid.fit(X_train, y_train, sample_weight=sw_train)

    best_model = grid.best_estimator_
    print(f"✅ Best Parameters: {grid.best_params_}")

    # Refit with early stopping
    best_model.fit(
        X_train, y_train,
        sample_weight=sw_train,
        eval_set=[(X_test, y_test)],
        early_stopping_rounds=30,
        verbose=True
    )

    # Evaluate
    y_pred = best_model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\n✅ Model trained. Test Accuracy: {acc:.2f}\n")

    cm = confusion_matrix(y_test, y_pred)
    cm_df = pd.DataFrame(cm, index=label_encoder.classes_, columns=label_encoder.classes_)
    cm_df.to_csv(os.path.join(os.path.dirname(DATASET_PATH), "confusion_matrix.csv"))
    print("📊 Confusion matrix saved at datasets/confusion_matrix.csv")

    # Save model + encoder
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(best_model, MODEL_PATH)
    joblib.dump(label_encoder, ENCODER_PATH)

    return best_model, label_encoder

def load_model():
    """Load or train model if not available."""
    if not os.path.exists(MODEL_PATH) or not os.path.exists(ENCODER_PATH):
        return train_and_save_model()
    model = joblib.load(MODEL_PATH)
    label_encoder = joblib.load(ENCODER_PATH)
    return model, label_encoder

# Load model at import
model, label_encoder = load_model()

# =====================================================
# Helpers
# =====================================================
def _make_input_row(symptoms_dict: dict) -> pd.DataFrame:
    input_data = pd.DataFrame([[0] * len(symptom_columns)], columns=symptom_columns)
    if isinstance(symptoms_dict, dict):
        for symptom, value in symptoms_dict.items():
            col = str(symptom)
            if col in input_data.columns:
                try:
                    input_data.at[0, col] = int(bool(value))
                except Exception:
                    input_data.at[0, col] = 1 if value else 0
    return input_data

# =====================================================
# Public API
# =====================================================
def predict_disease(symptoms_dict):
    input_data = _make_input_row(symptoms_dict)
    try:
        prediction_encoded = model.predict(input_data)[0]
        predicted_disease = label_encoder.inverse_transform([prediction_encoded])[0]
        return predicted_disease
    except Exception as e:
        print("⚠️ Prediction failed:", e)
        return None

def predict_disease_with_proba(symptoms_dict):
    input_data = _make_input_row(symptoms_dict)
    try:
        probs = model.predict_proba(input_data)[0]
        classes = list(model.classes_)

        pred_encoded = model.predict(input_data)[0]
        try:
            class_index = classes.index(pred_encoded)
            confidence = float(probs[class_index])
        except Exception:
            confidence = float(probs.max())

        label = label_encoder.inverse_transform([pred_encoded])[0]
        top_prediction = {"disease": label, "prob": confidence}
        return label, confidence, [top_prediction]
    except Exception as e:
        print("⚠️ Prediction with probability failed:", e)
        return None, 0.0, []

def get_all_symptoms():
    return symptom_columns
