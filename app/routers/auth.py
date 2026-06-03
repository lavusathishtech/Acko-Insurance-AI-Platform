from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import authenticate_user, create_access_token, get_current_user
from app.schemas import LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
async def login(payload: LoginRequest):
    user = authenticate_user(payload.email, payload.password, admin_only=False)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": str(user["id"]), "email": user["email"], "role": user["role"]})
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.post("/admin/login")
async def admin_login(payload: LoginRequest):
    user = authenticate_user(payload.email, payload.password, admin_only=True)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credentials")
    token = create_access_token({"sub": str(user["id"]), "email": user["email"], "role": user["role"]})
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user
