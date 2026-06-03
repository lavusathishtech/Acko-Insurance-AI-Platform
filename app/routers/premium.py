from __future__ import annotations

import datetime as dt
from typing import Any

from fastapi import APIRouter

from app.schemas import PremiumRequest
from app.services.insurance_logic import city_tier, engine_cc, fuel_factor, model_factor
from premium_engine import predict_premium

router = APIRouter(tags=["premium"])


@router.post("/predict-premium")
async def predict_premium_endpoint(payload: PremiumRequest) -> dict[str, Any]:
    vehicle_age = max(0, dt.date.today().year - payload.year)
    tier = city_tier(payload.city)
    cc = engine_cc(payload.vehicle_type, payload.model, payload.fuel_type)
    base_premium, source = predict_premium(
        vehicle_type=payload.vehicle_type,
        vehicle_age=vehicle_age,
        idv=payload.idv,
        city_tier=tier,
        ncb_percent=payload.ncb,
        policy_type="Comprehensive",
        engine_cc=cc,
        num_addons=2 if payload.vehicle_type.lower() == "car" else 1,
        claim_history_count=0,
    )
    adjusted = round(base_premium * model_factor(payload.model) * fuel_factor(payload.fuel_type), 2)
    own_damage = round(payload.idv * (0.026 if payload.vehicle_type.lower() == "car" else 0.019), 2)
    ncb_discount = round(own_damage * (payload.ncb / 100), 2)
    recommendation = "Comprehensive with zero-dep add-on recommended" if payload.ncb >= 20 else "Consider NCB transfer for savings"

    return {
        "predicted_premium": adjusted,
        "source": source,
        "currency": "INR",
        "recommendation": recommendation,
        "inputs": payload.model_dump(),
        "breakdown": {
            "vehicle_age": vehicle_age,
            "city_tier": tier,
            "engine_cc": cc,
            "own_damage_estimate": own_damage,
            "ncb_discount": ncb_discount,
            "tax_rate": "18%",
        },
    }
