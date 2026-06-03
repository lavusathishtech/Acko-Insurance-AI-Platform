from __future__ import annotations

from typing import Any


def assess_fraud_risk(
    analysis: dict[str, Any],
    approval_probability: float,
    description: str,
    file_size: int,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    score = 0
    severity = int(analysis.get("severity_score", 0) or 0)
    if severity >= 2 and approval_probability < 0.6:
        score += 2
        reasons.append("High severity with low approval confidence")
    if approval_probability < 0.55:
        score += 2
        reasons.append("Very low approval probability")
    lowered = description.lower()
    if any(w in lowered for w in ("already repaired", "no photo", "unknown", "staged")):
        score += 2
        reasons.append("Suspicious claim description")
    if file_size < 5000:
        score += 1
        reasons.append("Very small image file")
    if score >= 3:
        return "high", reasons
    if score >= 1:
        return "medium", reasons
    return "low", reasons
