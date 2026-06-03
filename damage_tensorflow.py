"""Optional TensorFlow damage severity classifier with heuristic fallback."""
from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


MODEL_CANDIDATES = (
    "models/damage_model.keras",
    "models/damage_model.h5",
)


def _load_model():
    from pathlib import Path

    root = Path(__file__).resolve().parent
    for rel in MODEL_CANDIDATES:
        path = root / rel
        if path.exists():
            import tensorflow as tf

            return tf.keras.models.load_model(str(path))
    return None


def _image_features(file_bytes: bytes) -> np.ndarray:
    image = Image.open(io.BytesIO(file_bytes)).convert("RGB").resize((224, 224))
    arr = np.array(image, dtype=np.float32) / 255.0
    return arr.reshape(1, 224, 224, 3)


def predict_damage_tensorflow(file_bytes: bytes) -> dict[str, Any]:
    model = _load_model()
    arr = _image_features(file_bytes)
    if model is not None:
        pred = model.predict(arr, verbose=0)
        if pred.ndim > 1 and pred.shape[-1] >= 3:
            idx = int(np.argmax(pred[0]))
        else:
            idx = int(round(float(pred[0][0]) * 2))
        severity_map = {0: ("minor", 0, "scratch"), 1: ("moderate", 1, "dent_or_crack"), 2: ("major", 2, "major_structural")}
        severity, score, dtype = severity_map.get(min(idx, 2), severity_map[1])
        return {
            "vehicle_type": "car",
            "damage_type": dtype,
            "affected_parts": ["body panel"],
            "severity": severity,
            "severity_score": score,
            "parts_count": 1 + score,
            "description": f"TensorFlow classified as {severity} damage.",
        }

    # Heuristic from image statistics when no trained weights
    image = Image.open(io.BytesIO(file_bytes)).convert("L")
    pixels = np.array(image, dtype=np.float32)
    contrast = float(pixels.std())
    dark_ratio = float((pixels < 60).mean())
    if contrast > 55 or dark_ratio > 0.35:
        return {
            "vehicle_type": "car",
            "damage_type": "major_structural",
            "affected_parts": ["body panel", "bumper"],
            "severity": "major",
            "severity_score": 2,
            "parts_count": 2,
            "description": "TensorFlow heuristic: high visual damage indicators.",
        }
    if contrast > 35:
        return {
            "vehicle_type": "car",
            "damage_type": "dent_or_crack",
            "affected_parts": ["body panel"],
            "severity": "moderate",
            "severity_score": 1,
            "parts_count": 1,
            "description": "TensorFlow heuristic: moderate damage indicators.",
        }
    return {
        "vehicle_type": "car",
        "damage_type": "scratch",
        "affected_parts": ["body panel"],
        "severity": "minor",
        "severity_score": 0,
        "parts_count": 1,
        "description": "TensorFlow heuristic: minor surface damage.",
    }
