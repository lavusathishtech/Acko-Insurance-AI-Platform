from __future__ import annotations

from fastapi import APIRouter

from app.schemas import ChatRequest
from app.services.chatbot import chat_reply

router = APIRouter(tags=["chatbot"])


@router.post("/chatbot")
async def chatbot_endpoint(payload: ChatRequest):
    return chat_reply(payload.message, payload.lang)
