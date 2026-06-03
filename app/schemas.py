from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field


class PremiumRequest(BaseModel):
    vehicle_type: str = Field(..., min_length=2)
    model: str = Field(..., min_length=1)
    year: int = Field(..., ge=1995, le=dt.date.today().year)
    fuel_type: str = Field(..., min_length=2)
    city: str = Field(..., min_length=2)
    idv: float = Field(..., gt=0)
    ncb: int = Field(..., ge=0, le=50)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    lang: str = Field(default="en", max_length=10)


class LoginRequest(BaseModel):
    email: str
    password: str
