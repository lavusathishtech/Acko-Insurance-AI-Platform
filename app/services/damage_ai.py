from __future__ import annotations

import io
import os
from typing import Any

from app.config import ENABLE_GEMINI_DAMAGE, ENABLE_TENSORFLOW_DAMAGE
from app.services.insurance_logic import fallback_damage


def analyse_damage(file_bytes: bytes, description: str) -> tuple[dict[str, Any], str]:
    if ENABLE_TENSORFLOW_DAMAGE:
        try:
            from damage_tensorflow import predict_damage_tensorflow

            analysis = predict_damage_tensorflow(file_bytes)
            return analysis, "TensorFlow damage model"
        except Exception:
            pass

    if ENABLE_GEMINI_DAMAGE and os.getenv("GEMINI_API_KEY"):
        try:
            from damage_engine import analyse_damage_photo

            analysis = analyse_damage_photo(file_bytes)
            return analysis, "Gemini vision analysis"
        except Exception:
            pass

    return fallback_damage(description, file_bytes), "Heuristic damage analysis"
