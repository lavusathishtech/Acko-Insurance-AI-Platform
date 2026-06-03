from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(_user: dict = Depends(get_current_user)):
    return [
        {"id": 1, "title": "Renewal reminder", "message": "Your car policy renews in 30 days.", "read": False},
        {"id": 2, "title": "Claim update", "message": "Claim is under AI review.", "read": False},
    ]
