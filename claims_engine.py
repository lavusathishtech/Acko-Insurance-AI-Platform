"""
Module 3 — AI Claims Engine integration.
Trains/loads 4 Gradient Boosting models (car/bike amount + approval),
optional Gemini Vision damage analysis, and heuristic fallbacks.
"""

from __future__ import annotations

import io
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv
import boto3
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.model_selection import train_test_split

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
MODEL_DIR.mkdir(exist_ok=True)

FEATURES = [
    "idv",
    "vehicle_age",
    "damage_severity",
    "parts_affected",
    "claim_history",
    "policy_type",
    "ncb",
    "reported_within_days",
]

_MODEL_CACHE: dict[str, Any] | None = None


def generate_claims_data(n: int = 2000, vehicle: str = "car") -> pd.DataFrame:
    """Synthetic training data matching Module3 notebook logic."""
    rng = np.random.default_rng(42 if vehicle == "car" else 43)
    if vehicle == "car":
        idv = rng.integers(200_000, 2_000_000, n)
        base_pct = 0.08
    else:
        idv = rng.integers(30_000, 200_000, n)
        base_pct = 0.10

    vehicle_age = rng.integers(0, 12, n)
    damage_severity = rng.choice([0, 1, 2], n, p=[0.4, 0.35, 0.25])
    parts_affected = rng.integers(1, 6, n)
    claim_history = rng.integers(0, 4, n)
    policy_type = rng.choice([0, 1], n, p=[0.3, 0.7])
    ncb = rng.choice([0, 20, 25, 35, 50], n)
    reported_within_days = rng.integers(1, 30, n)

    severity_mult = {0: 0.5, 1: 1.0, 2: 1.8}
    sev_m = np.vectorize(severity_mult.get)(damage_severity)
    claim_amount = (idv * base_pct * sev_m * (1 + 0.1 * parts_affected)).astype(int)
    claim_amount = np.minimum(claim_amount, idv)

    approval_score = (
        0.25
        + 0.25 * policy_type
        + 0.15 * (1 - claim_history / 5)
        + 0.15 * (1 - reported_within_days / 30)
        + 0.1 * (ncb / 50)
        - 0.35 * (damage_severity / 2)
        + rng.normal(0, 0.08, n)
    )
    approved = (approval_score > 0.45).astype(int)

    return pd.DataFrame(
        {
            "idv": idv,
            "vehicle_age": vehicle_age,
            "damage_severity": damage_severity,
            "parts_affected": parts_affected,
            "claim_history": claim_history,
            "policy_type": policy_type,
            "ncb": ncb,
            "reported_within_days": reported_within_days,
            "claim_amount": claim_amount,
            "approved": approved,
        }
    )


def _train_pair(df: pd.DataFrame) -> tuple[Any, Any]:
    X = df[FEATURES]
    y_amt = df["claim_amount"]
    y_ap = df["approved"]
    X_tr, X_te, y_amt_tr, y_amt_te, y_ap_tr, y_ap_te = train_test_split(
        X, y_amt, y_ap, test_size=0.2, random_state=42, stratify=y_ap
    )
    reg = GradientBoostingRegressor(n_estimators=120, random_state=42)
    reg.fit(X_tr, y_amt_tr)
    clf = GradientBoostingClassifier(n_estimators=120, random_state=42)
    clf.fit(X_tr, y_ap_tr)
    return reg, clf


def ensure_models() -> dict[str, Any]:
    """Load or train the four Module 3 models."""
    global _MODEL_CACHE
    if _MODEL_CACHE is not None:
        return _MODEL_CACHE

    paths = {
        "car_amount": MODEL_DIR / "model1_car_amount.pkl",
        "car_approval": MODEL_DIR / "model2_car_approval.pkl",
        "bike_amount": MODEL_DIR / "model3_bike_amount.pkl",
        "bike_approval": MODEL_DIR / "model4_bike_approval.pkl",
    }

    # If models are stored in S3, download missing ones
    bucket = os.getenv("MODEL_S3_BUCKET")
    if bucket:
        load_models_from_s3(bucket)
    if all(p.exists() for p in paths.values()):
        try:
            _MODEL_CACHE = {k: joblib.load(p) for k, p in paths.items()}
            return _MODEL_CACHE
        except Exception as e:
            print(f"Model loading error: {e}. Regenerating models.")
    # If loading failed or models missing, train anew
    car_df = generate_claims_data(2500, "car")
    bike_df = generate_claims_data(2500, "bike")
    car_reg, car_clf = _train_pair(car_df)
    bike_reg, bike_clf = _train_pair(bike_df)

    joblib.dump(car_reg, paths["car_amount"])
    joblib.dump(car_clf, paths["car_approval"])
    joblib.dump(bike_reg, paths["bike_amount"])
    joblib.dump(bike_clf, paths["bike_approval"])

    _MODEL_CACHE = {
        "car_amount": car_reg,
        "car_approval": car_clf,
        "bike_amount": bike_reg,
        "bike_approval": bike_clf,
    }
    return _MODEL_CACHE


def load_models_from_s3(bucket: str):
    """Download missing model files from the given S3 bucket.
    Expects models stored under the 'models/' prefix matching the filenames.
    """
    s3 = boto3.client('s3')
    for name, path in paths.items():
        if not path.exists():
            key = f"models/{path.name}"
            try:
                s3.download_file(bucket, key, str(path))
                print(f"Downloaded {key} from S3 bucket {bucket}")
            except Exception as e:
                print(f"Failed to download {key} from S3: {e}")


    joblib.dump(car_reg, paths["car_amount"])
    joblib.dump(car_clf, paths["car_approval"])
    joblib.dump(bike_reg, paths["bike_amount"])
    joblib.dump(bike_clf, paths["bike_approval"])

    _MODEL_CACHE = {
        "car_amount": car_reg,
        "car_approval": car_clf,
        "bike_amount": bike_reg,
        "bike_approval": bike_clf,
    }
    return _MODEL_CACHE


def _heuristic_damage_analysis(description: str, vehicle_type: str) -> dict[str, Any]:
    """Fallback when Gemini is unavailable."""
    text = (description or "").lower()
    severity_score = 1
    if any(w in text for w in ("total loss", "major", "fire", "flood", "structural")):
        severity_score = 2
    elif any(w in text for w in ("scratch", "minor", "small")):
        severity_score = 0

    parts_count = 2
    if any(w in text for w in ("bumper", "headlight", "bonnet", "door")):
        parts_count = 3
    if severity_score == 2:
        parts_count = max(parts_count, 4)

    damage_type = "dent"
    if "crack" in text or "glass" in text:
        damage_type = "crack"
    elif severity_score == 2:
        damage_type = "major_structural"

    return {
        "vehicle_type": vehicle_type.lower(),
        "damage_type": damage_type,
        "affected_parts": ["bumper", "panel"] if parts_count >= 2 else ["panel"],
        "severity": ["minor", "moderate", "major"][severity_score],
        "severity_score": severity_score,
        "parts_count": parts_count,
        "description": description or "Damage reported via customer portal upload.",
        "analysis_source": "heuristic",
    }


def _gemini_vision_models() -> list[str]:
    configured = os.getenv("GEMINI_VISION_MODEL", os.getenv("GEMINI_MODEL", "")).strip()
    candidates = [
        configured,
        "gemini-2.5-flash-lite",
        "gemini-flash-latest",
        "gemini-2.0-flash-lite",
    ]
    seen: set[str] = set()
    return [m for m in candidates if m and not (m in seen or seen.add(m))]


def _parse_vision_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def analyse_damage_photo_bytes(image_bytes: bytes, description: str, vehicle_type: str) -> dict[str, Any]:
    """Gemini Vision analysis with heuristic fallback."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "YOUR_GEMINI_KEY":
        return _heuristic_damage_analysis(description, vehicle_type)

    from google import genai
    from google.genai import types

    prompt = """
You are an expert motor insurance damage assessor. Analyse the vehicle damage photo.
Respond ONLY with valid JSON (no markdown fences):
{"vehicle_type":"car or bike","damage_type":"scratch/dent/crack/major_structural",
"affected_parts":["part1","part2"],"severity":"minor/moderate/major","severity_score":0,
"parts_count":2,"description":"one sentence"}
Use severity_score: 0=minor, 1=moderate, 2=major.
"""
    for model_name in _gemini_vision_models():
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    prompt,
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type="image/jpeg",
                    ),
                ],
            )
            data = _parse_vision_json(response.text or "")
            data["analysis_source"] = f"gemini_vision ({model_name})"
            return data
        except Exception:
            continue

    return _heuristic_damage_analysis(description, vehicle_type)


def build_features(damage_info: dict[str, Any], form_data: dict[str, Any]) -> pd.DataFrame:
    """Build ML feature row from vision output and form fields."""
    policy_type_encoded = (
        1 if str(form_data.get("policy_type", "")).lower() == "comprehensive" else 0
    )
    try:
        incident = datetime.strptime(form_data.get("incident_date", "2024-01-01"), "%Y-%m-%d")
        days_reported = min((datetime.now() - incident).days, 30)
    except Exception:
        days_reported = 7

    row = {
        "idv": float(form_data.get("idv") or 500_000),
        "vehicle_age": int(form_data.get("vehicle_age_years") or 3),
        "damage_severity": int(damage_info.get("severity_score", 1)),
        "parts_affected": int(damage_info.get("parts_count", 2)),
        "claim_history": int(form_data.get("claim_history_count") or 0),
        "policy_type": policy_type_encoded,
        "ncb": int(form_data.get("ncb_percent") or 0),
        "reported_within_days": days_reported,
    }
    return pd.DataFrame([row])


def predict_claim(
    image_bytes: bytes,
    form_data: dict[str, Any],
    description: str = "",
) -> dict[str, Any]:
    """
    Full Module 3 pipeline: vision analysis → feature build → routed ML prediction.
    """
    models = ensure_models()
    vehicle_hint = str(form_data.get("vehicle_type", "car")).lower()
    damage_info = analyse_damage_photo_bytes(image_bytes, description, vehicle_hint)

    vehicle_type = (
        str(damage_info.get("vehicle_type") or form_data.get("vehicle_type") or "car")
    ).lower()
    if vehicle_type not in ("car", "bike"):
        vehicle_type = "car"

    X = build_features(damage_info, form_data)

    if vehicle_type == "bike":
        amount = float(models["bike_amount"].predict(X)[0])
        approval_p = float(models["bike_approval"].predict_proba(X)[0][1])
        model_used = "Model 3 + Model 4 (Bike)"
    else:
        amount = float(models["car_amount"].predict(X)[0])
        approval_p = float(models["car_approval"].predict_proba(X)[0][1])
        model_used = "Model 1 + Model 2 (Car)"

    approval_pct = round(approval_p * 100, 1)
    fraud_risk = round(max(0, min(100, (100 - approval_pct) * 0.85 + form_data.get("claim_history_count", 0) * 8)), 1)

    if approval_pct >= 75:
        status = "Approved"
    elif approval_pct >= 50:
        status = "Under Review"
    else:
        status = "Escalated"

    claim_id = f"CLM-{uuid.uuid4().hex[:8].upper()}"

    return {
        "claim_id": claim_id,
        "claim_reference": claim_id,
        "vehicle_type": vehicle_type,
        "model_used": model_used,
        "predicted_amount": int(max(amount, 0)),
        "estimated_amount": int(max(amount, 0)),
        "approval_probability": approval_pct / 100,
        "approval_percent": approval_pct,
        "fraud_probability": fraud_risk,
        "status": status,
        "analysis": {
            "severity": damage_info.get("severity", "moderate"),
            "damage_type": damage_info.get("damage_type", "dent"),
            "affected_parts": damage_info.get("affected_parts", []),
            "severity_score": damage_info.get("severity_score", 1),
            "parts_count": damage_info.get("parts_count", 2),
            "description": damage_info.get("description", description),
            "source": damage_info.get("analysis_source", "heuristic"),
        },
        "damage_info": damage_info,
    }
