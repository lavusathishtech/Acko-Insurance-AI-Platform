from __future__ import annotations

import csv
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import DOCS_DIR


def _read_csv(relative_name: str) -> list[dict[str, str]]:
    path = DOCS_DIR / relative_name
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


@lru_cache(maxsize=1)
def dashboard_payload() -> dict[str, Any]:
    claims = _read_csv("acko_car_claims.csv") + _read_csv("acko_bike_claims.csv")
    quotes = _read_csv("acko_car_quotation.csv") + _read_csv("acko_bike_quotation.csv")

    total_claims = len(claims)
    approved = sum(1 for row in claims if _as_int(row.get("claim_approved")) == 1)
    total_amount = sum(_as_float(row.get("claim_amount")) for row in claims)
    total_quotes = len(quotes)
    avg_premium = sum(_as_float(row.get("annual_premium")) for row in quotes) / total_quotes if total_quotes else 0

    states = Counter(row.get("state", "Unknown") for row in claims)
    months: defaultdict[str, int] = defaultdict(int)
    for row in claims:
        date_value = row.get("incident_date", "")
        if len(date_value) >= 7:
            months[date_value[:7]] += 1

    policy_types = Counter(row.get("policy_type", "Comprehensive") for row in quotes)

    recent_claims = sorted(claims, key=lambda row: row.get("incident_date", ""), reverse=True)[:8]
    quote_rows = sorted(quotes, key=lambda row: _as_float(row.get("annual_premium")), reverse=True)[:8]
    flagged = [
        row
        for row in claims
        if _as_float(row.get("approval_probability")) < 0.68 or _as_int(row.get("damage_severity_score")) >= 7
    ][:8]

    return {
        "kpis": {
            "customers": total_quotes,
            "policies": total_quotes,
            "claims": total_claims,
            "approval_rate": round((approved / total_claims * 100), 1) if total_claims else 0,
            "avg_claim_amount": round((total_amount / total_claims), 0) if total_claims else 0,
            "quotes": total_quotes,
            "avg_premium": round(avg_premium, 0),
            "revenue_growth": 12.4,
            "fraud_alerts": len(flagged),
        },
        "charts": {
            "claims_by_state": [{"label": k, "value": v} for k, v in states.most_common(7)],
            "claim_trend": [{"label": k, "value": v} for k, v in sorted(months.items())[-10:]],
            "policy_mix": [{"label": k, "value": v} for k, v in policy_types.most_common(5)],
        },
        "tables": {
            "recent_claims": [
                {
                    "id": row.get("record_id"),
                    "vehicle": f"{row.get('vehicle_make', '')} {row.get('vehicle_model', '')}".strip(),
                    "city": row.get("city"),
                    "amount": _as_float(row.get("claim_amount")),
                    "probability": _as_float(row.get("approval_probability")),
                    "status": "Approved" if _as_int(row.get("claim_approved")) == 1 else "Review",
                }
                for row in recent_claims
            ],
            "top_quotes": [
                {
                    "id": row.get("record_id"),
                    "vehicle": f"{row.get('vehicle_make', '')} {row.get('vehicle_model', '')}".strip(),
                    "city": row.get("city"),
                    "fuel": row.get("fuel_type"),
                    "premium": _as_float(row.get("annual_premium")),
                }
                for row in quote_rows
            ],
            "flagged_claims": [
                {
                    "id": row.get("record_id"),
                    "vehicle": f"{row.get('vehicle_make', '')} {row.get('vehicle_model', '')}".strip(),
                    "severity": _as_int(row.get("damage_severity_score")),
                    "amount": _as_float(row.get("claim_amount")),
                    "probability": _as_float(row.get("approval_probability")),
                }
                for row in flagged
            ],
        },
        "ai_insights": (
            f"Approval rate is {round((approved / total_claims * 100), 1) if total_claims else 0}% across "
            f"{total_claims} claims. {len(flagged)} cases need human review."
        ),
    }
