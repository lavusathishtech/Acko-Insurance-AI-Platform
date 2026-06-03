from __future__ import annotations

from pathlib import Path

import numpy as np


MODEL_CANDIDATES = (
    "models/premium_model.joblib",
    "models/premium_model.pkl",
    "premium_model.joblib",
    "premium_model.pkl",
)


def project_root() -> Path:
    return Path(__file__).resolve().parent


def find_model_path() -> Path | None:
    root = project_root()
    for relative_path in MODEL_CANDIDATES:
        path = root / relative_path
        if path.exists():
            return path
    return None


def load_model():
    path = find_model_path()
    if path is None:
        return None, None

    import joblib

    return joblib.load(path), path


def fallback_premium(
    vehicle_type: str,
    vehicle_age: int,
    idv: float,
    city_tier: int,
    ncb_percent: int,
    policy_type: str,
    engine_cc: int,
    num_addons: int,
    claim_history_count: int,
) -> float:
    is_car = vehicle_type.lower() == "car"
    base_rate = 0.032 if is_car else 0.022
    if policy_type == "Third Party":
        base_rate = 0.012 if is_car else 0.009

    age_factor = 1 + min(vehicle_age, 15) * 0.025
    city_factor = {1: 1.16, 2: 1.08, 3: 1.0}.get(int(city_tier), 1.0)
    cc_factor = 1 + max(engine_cc - (1200 if is_car else 150), 0) / (90000 if is_car else 30000)
    claim_factor = 1 + min(claim_history_count, 5) * 0.12
    addon_amount = max(0, num_addons) * (850 if is_car else 280)

    own_damage = idv * base_rate * age_factor * city_factor * cc_factor * claim_factor
    ncb_discount = own_damage * (max(0, min(ncb_percent, 50)) / 100)
    third_party = 3416 if is_car else 714
    subtotal = max(0, own_damage - ncb_discount) + third_party + addon_amount
    return round(subtotal * 1.18, 2)


def predict_premium(
    vehicle_type: str,
    vehicle_age: int,
    idv: float,
    city_tier: int,
    ncb_percent: int,
    policy_type: str,
    engine_cc: int,
    num_addons: int,
    claim_history_count: int,
) -> tuple[float, str]:
    model, model_path = load_model()
    if model is not None:
        features = np.array(
            [[
                1 if vehicle_type.lower() == "car" else 0,
                vehicle_age,
                idv,
                city_tier,
                ncb_percent,
                1 if policy_type == "Comprehensive" else 0,
                engine_cc,
                num_addons,
                claim_history_count,
            ]]
        )
        try:
            prediction = float(model.predict(features)[0])
            return round(prediction, 2), f"Model: {model_path.name}"
        except Exception:
            pass

    return fallback_premium(
        vehicle_type=vehicle_type,
        vehicle_age=vehicle_age,
        idv=idv,
        city_tier=city_tier,
        ncb_percent=ncb_percent,
        policy_type=policy_type,
        engine_cc=engine_cc,
        num_addons=num_addons,
        claim_history_count=claim_history_count,
    ), "Fallback estimate"

