from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.auth import get_current_user
from app.services.policy_pdf import generate_policy_pdf

router = APIRouter(prefix="/api/policies", tags=["policies"])

DEMO_POLICIES = {
    1: {"id": 1, "vehicle": "Honda Amaze", "policy_type": "Comprehensive", "premium": 12840, "idv": 450000, "status": "active"},
    2: {"id": 2, "vehicle": "Royal Enfield Classic", "policy_type": "Third Party", "premium": 2140, "idv": 95000, "status": "active"},
}


@router.get("/{policy_id}/pdf")
async def download_policy_pdf(policy_id: int, _user: dict = Depends(get_current_user)):
    policy = DEMO_POLICIES.get(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    path = generate_policy_pdf(policy)
    media = "application/pdf" if path.suffix == ".pdf" else "text/plain"
    return FileResponse(path, media_type=media, filename=path.name)
