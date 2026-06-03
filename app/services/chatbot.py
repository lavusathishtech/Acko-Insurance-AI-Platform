from __future__ import annotations

import os

from app.config import ENABLE_GEMINI_CHAT


def chat_reply(message: str, lang: str = "en") -> dict:
    message = message.strip()
    prefix = ""
    if lang == "hi":
        prefix = "[Respond in simple Hindi] "

    if ENABLE_GEMINI_CHAT and os.getenv("GEMINI_API_KEY"):
        try:
            from faq_engine import answer_faq

            reply, source = answer_faq(prefix + message, top_k=8)
            return {"reply": reply, "confidence": 0.86, "source": source}
        except Exception:
            pass

    lowered = message.lower()
    if "claim" in lowered:
        reply = (
            "You can file a claim by uploading the damage photo, adding the incident date, "
            "and describing what happened. The AI estimate shows an amount and approval probability instantly."
        )
    elif any(w in lowered for w in ("premium", "quote", "price")):
        reply = (
            "Your premium is mainly influenced by IDV, vehicle age, city tier, fuel type, "
            "engine size, NCB, and selected add-ons."
        )
    elif "ncb" in lowered or "no claim" in lowered:
        reply = "NCB is a discount for claim-free policy years on the own-damage portion of premium."
    elif "idv" in lowered:
        reply = "IDV is the insured declared value — the maximum sum insured for your vehicle."
    elif "family" in lowered or "health" in lowered:
        reply = "Family and health plans bundle hospitalization cover. Compare sum insured and waiting periods."
    elif "travel" in lowered:
        reply = "Travel insurance covers trip cancellation, medical emergencies, and baggage loss abroad."
    else:
        reply = (
            "I can help with quotes, claims, NCB, IDV, and policy coverage. "
            "Ask about car, bike, health, travel, or family insurance."
        )

    if lang == "hi":
        reply += " (English demo — enable Gemini for full Hindi responses.)"

    return {"reply": reply, "confidence": 0.74, "source": "Local insurance assistant"}
