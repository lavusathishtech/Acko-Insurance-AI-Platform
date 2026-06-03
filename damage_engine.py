"""
Damage analysis helpers used by app routers (Gemini / heuristic fallbacks).
"""

from __future__ import annotations

import os
from typing import Any

from app.services.insurance_logic import fallback_damage

_SEVERITY_MULT = {0: 0.08, 1: 0.14, 2: 0.22}


def estimate_claim_amount(analysis: dict[str, Any], idv: float) -> int:
    """Estimate claim payout from damage analysis and IDV."""
    score = int(analysis.get("severity_score", 1) or 1)
    parts = max(1, int(analysis.get("parts_count", 1) or 1))
    mult = _SEVERITY_MULT.get(score, 0.14)
    amount = int(idv * mult * (1 + 0.05 * (parts - 1)))
    return min(amount, int(idv))


def analyse_damage_photo(file_bytes: bytes) -> dict[str, Any]:
    """Optional Gemini vision analysis; falls back to heuristics."""
    key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if key:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=key)
            prompt = (
                "Analyze this vehicle damage image. Reply in one short paragraph: "
                "severity (minor/moderate/major), damaged parts, and damage type."
            )
            response = client.models.generate_content(
                model="gemini-2.0-flash-lite",
                contents=[
                    prompt,
                    types.Part.from_bytes(
                        data=file_bytes,
                        mime_type="image/jpeg",
                    ),
                ],
            )
            text = (response.text or "").strip()
            return fallback_damage(text, file_bytes)
        except Exception:
            pass
    return fallback_damage("", file_bytes)
