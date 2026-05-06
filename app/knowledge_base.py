import json
from pathlib import Path
from functools import lru_cache

ROOT = Path(__file__).resolve().parent
KB_PATH = ROOT / "disease_knowledge.json"

@lru_cache(maxsize=1)
def _load():
    if not KB_PATH.exists():
        raise FileNotFoundError(f"Knowledge base not found at {KB_PATH}. Run build_knowledge_json.py first.")
    with KB_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    # Normalize keys to lowercase, but keep original data
    index = {k.lower(): k for k in data.keys()}
    return data, index

def get_all_diseases():
    data, _ = _load()
    return sorted(list(data.keys()))

def get_info(disease: str):
    """Case-insensitive fetch."""
    if not disease:
        return None
    data, index = _load()
    key = index.get(disease.lower())
    return data.get(key) if key else None

def get_all_symptoms():
    """Union of symptom lists across all diseases in the KB."""
    data, _ = _load()
    s = set()
    for v in data.values():
        for sym in v.get("symptoms", []):
            s.add(sym)
    return sorted(s)

def best_match_by_overlap(input_syms, top_k=3):
    """Simple rule-based ranker: overlap count with KB symptoms."""
    data, _ = _load()
    in_set = set(sym.strip().lower() for sym in input_syms if str(sym).strip())
    scores = []
    for disease, payload in data.items():
        kb_set = set(s.lower() for s in payload.get("symptoms", []))
        overlap = len(in_set & kb_set)
        if overlap > 0:
            scores.append((overlap, disease))
    scores.sort(key=lambda x: (-x[0], x[1]))
    return [d for _, d in scores[:top_k]]
