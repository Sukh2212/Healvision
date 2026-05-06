# app/data_loader.py
import pandas as pd
import os
import re

# Path to datasets folder (project root /datasets)
DATASETS_DIR = os.path.join(os.getcwd(), "datasets")

# helper normalization
def _norm(s):
    if s is None:
        return ""
    return str(s).strip().lower()

# split a cell into list items by common separators
def _split_items(cell):
    if pd.isna(cell):
        return []
    if isinstance(cell, (list, tuple)):
        items = [str(x).strip() for x in cell if str(x).strip()]
        return items
    s = str(cell)
    # split on comma, semicolon, pipe, newline
    parts = re.split(r',|\||;|\n', s)
    return [p.strip() for p in parts if p.strip()]

def _guess_disease_column(df):
    # common names for disease column
    for col in df.columns:
        if col.lower() in ("disease", "diseases", "prognosis", "illness", "name"):
            return col
    # fallback to first column
    return df.columns[0]

def load_list_map(csv_filename):
    """
    Load a CSV and produce {normalized_disease: [values,...]} where values are
    collected from every column except the disease column (split if needed).
    """
    path = os.path.join(DATASETS_DIR, csv_filename)
    if not os.path.exists(path):
        return {}
    df = pd.read_csv(path)
    disease_col = _guess_disease_column(df)
    value_cols = [c for c in df.columns if c != disease_col]
    mapping = {}
    for _, row in df.iterrows():
        disease = _norm(row[disease_col])
        if not disease:
            continue
        vals = []
        for c in value_cols:
            vals.extend(_split_items(row[c]))
        # dedupe while preserving order
        seen = set()
        clean = []
        for v in vals:
            if not v:
                continue
            if v.lower() not in seen:
                seen.add(v.lower())
                clean.append(v)
        mapping[disease] = clean
    return mapping

def load_text_map(csv_filename):
    """
    Load a CSV and produce {normalized_disease: "long description string"} by
    concatenating non-empty value columns (useful for description.csv).
    """
    path = os.path.join(DATASETS_DIR, csv_filename)
    if not os.path.exists(path):
        return {}
    df = pd.read_csv(path)
    disease_col = _guess_disease_column(df)
    value_cols = [c for c in df.columns if c != disease_col]
    mapping = {}
    for _, row in df.iterrows():
        disease = _norm(row[disease_col])
        if not disease:
            continue
        texts = []
        for c in value_cols:
            v = row[c]
            if pd.isna(v):
                continue
            texts.append(str(v).strip())
        mapping[disease] = " ".join(texts).strip()
    return mapping

# Load maps at import time (cached)
_medications_map = load_list_map("medications.csv")
_precautions_map = load_list_map("precautions_df.csv")
_workout_map = load_list_map("workout_df.csv")
_diets_map = load_list_map("diets.csv")
_description_map = load_text_map("description.csv")

def get_disease_info(disease_name):
    """
    Return a dict with keys:
      - medicines: list
      - precautions: list
      - exercises: list
      - diets: list
      - description: string
    disease_name lookup is case-insensitive.
    """
    if not disease_name:
        return {
            "medicines": [],
            "precautions": [],
            "exercises": [],
            "diets": [],
            "description": ""
        }
    key = _norm(disease_name)
    return {
        "medicines": _medications_map.get(key, []),
        "precautions": _precautions_map.get(key, []),
        "exercises": _workout_map.get(key, []),
        "diets": _diets_map.get(key, []),
        "description": _description_map.get(key, "")
    }
