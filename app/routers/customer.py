from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends

from app.auth import get_current_user

router = APIRouter(prefix="/api/customer", tags=["customer"])


@router.get("/overview")
async def customer_overview(user: dict = Depends(get_current_user)):
    today = dt.date.today()
    policies = [
        {
            "id": 1,
            "vehicle": "Honda Amaze",
            "policy_type": "Comprehensive",
            "premium": 12840,
            "idv": 450000,
            "status": "active",
            "pdf_available": True,
            "end_date": (today + dt.timedelta(days=180)).isoformat(),
        },
        {
            "id": 2,
            "vehicle": "Royal Enfield Classic",
            "policy_type": "Third Party",
            "premium": 2140,
            "idv": 95000,
            "status": "active",
            "pdf_available": True,
            "end_date": (today + dt.timedelta(days=90)).isoformat(),
        },
    ]
    claims = [
        {"id": "CLM-001", "reference": "CLM-2505271201", "status": "under review", "amount": 18500},
    ]
    notifications = [
        {"id": 1, "title": "Renewal reminder", "message": "Your car policy renews in 30 days."},
        {"id": 2, "title": "Claim update", "message": "Claim CLM-001 is being reviewed by our AI adjuster."},
    ]
    return {
        "user": user,
        "policies": policies,
        "claims": claims,
        "notifications": notifications,
        "total_premium": sum(p["premium"] for p in policies),
    }
