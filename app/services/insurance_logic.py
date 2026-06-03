from __future__ import annotations

import datetime as dt
from typing import Any


TIER_ONE_CITIES = {
    "ahmedabad", "bengaluru", "bangalore", "chennai", "delhi",
    "hyderabad", "kolkata", "mumbai", "pune",
}
TIER_TWO_CITIES = {
    "bhopal", "chandigarh", "coimbatore", "indore", "jaipur",
    "kochi", "lucknow", "nagpur", "surat", "vadodara", "visakhapatnam",
}


def city_tier(city: str) -> int:
    key = city.strip().lower()
    if key in TIER_ONE_CITIES:
        return 1
    if key in TIER_TWO_CITIES:
        return 2
    return 3


def engine_cc(vehicle_type: str, model: str, fuel_type: str) -> int:
    fuel = fuel_type.lower()
    model_key = model.lower()
    is_bike = vehicle_type.lower() in {"bike", "scooter"}
    if "electric" in fuel or "ev" in model_key:
        return 0
    if is_bike:
        if any(t in model_key for t in ("bullet", "classic", "ninja", "duke", "interceptor")):
            return 350
        return 150
    if any(t in model_key for t in ("fortuner", "xuv", "safari", "hector", "e-class", "q3", "x1")):
        return 1950
    if "diesel" in fuel:
        return 1498
    return 1199


def model_factor(model: str) -> float:
    model_key = model.lower()
    if any(t in model_key for t in ("bmw", "audi", "mercedes", "lexus", "volvo")):
        return 1.18
    if any(t in model_key for t in ("sport", "ninja", "duke", "gt", "rs")):
        return 1.08
    if any(t in model_key for t in ("alto", "wagon", "splendor", "activa", "fascino")):
        return 0.94
    return 1.0


def fuel_factor(fuel_type: str) -> float:
    fuel = fuel_type.lower()
    if "electric" in fuel:
        return 0.92
    if "diesel" in fuel:
        return 1.06
    if "cng" in fuel:
        return 0.96
    return 1.0


def fallback_damage(description: str, file_bytes: bytes) -> dict[str, Any]:
    text = description.lower()
    major_words = {"fire", "flood", "engine", "chassis", "total", "major", "shattered", "structural"}
    moderate_words = {"crack", "dent", "bumper", "door", "glass", "accident", "collision"}
    parts = [p for p in ("bumper", "door", "bonnet", "windshield", "engine", "mirror", "fender", "headlight") if p in text]
    if any(w in text for w in major_words) or len(file_bytes) > 1_500_000:
        severity_score, severity, damage_type = 2, "major", "major_structural"
    elif any(w in text for w in moderate_words) or len(file_bytes) > 150_000:
        severity_score, severity, damage_type = 1, "moderate", "dent_or_crack"
    else:
        severity_score, severity, damage_type = 0, "minor", "scratch"
    return {
        "vehicle_type": "car",
        "damage_type": damage_type,
        "affected_parts": parts or ["body panel"],
        "severity": severity,
        "severity_score": severity_score,
        "parts_count": max(1, len(parts)),
        "description": description or "Image-based FNOL submitted by customer.",
    }


def approval_probability(analysis: dict[str, Any], incident_date: str, description: str) -> float:
    severity_score = int(analysis.get("severity_score", 1) or 1)
    probability = 0.93 - (severity_score * 0.12)
    lowered = description.lower()
    if any(w in lowered for w in ("late", "unclear", "unknown", "no photo", "already repaired")):
        probability -= 0.08
    try:
        incident = dt.date.fromisoformat(incident_date)
        days_old = (dt.date.today() - incident).days
        if days_old > 30:
            probability -= 0.05
        if days_old > 180:
            probability -= 0.08
    except ValueError:
        probability -= 0.04
    return round(max(0.35, min(0.98, probability)), 4)
