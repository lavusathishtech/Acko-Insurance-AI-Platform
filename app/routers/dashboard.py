from __future__ import annotations

from fastapi import APIRouter

from app.services.dashboard import dashboard_payload

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard-data")
async def dashboard_data_endpoint():
    return dashboard_payload()
