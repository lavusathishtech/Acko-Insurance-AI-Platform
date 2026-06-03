from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
import json

import csv
import io

from app.auth import require_admin
from app.services.dashboard import dashboard_payload

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/dashboard")
async def admin_dashboard(_user: dict = Depends(require_admin)):
    return dashboard_payload()


@router.get("/report")
async def admin_report(type: str = "escalation", format: str = "csv", range: str = "all", _user: dict = Depends(require_admin)):
    """Generate a report (escalation desk, recent claims, or all) in CSV or JSON format."""
    payload = dashboard_payload()
    
    # Select data based on report type
    if type == "recent_claims":
        rows = payload.get("tables", {}).get("recent_claims", [])
        fields = ["id", "vehicle", "city", "amount", "probability", "status"]
    elif type == "all":
        # Combine all tables
        escalation = payload.get("tables", {}).get("flagged_claims", [])
        rows = escalation
        fields = ["id", "vehicle", "severity", "amount", "probability"]
    else:  # escalation (default)
        rows = payload.get("tables", {}).get("flagged_claims", [])
        fields = ["id", "vehicle", "severity", "amount", "probability"]

    # Return JSON format
    if format == "json":
        data = [
            {field: row.get(field) if isinstance(row, dict) else getattr(row, field, None) 
             for field in fields}
            for row in rows
        ]
        json_text = json.dumps(data, indent=2)
        headers = {"Content-Disposition": f'attachment; filename="admin_report_{type}.json"'}
        return Response(content=json_text, media_type="application/json", headers=headers)
    
    # CSV format (default)
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(fields)
    for row in rows:
        if isinstance(row, dict):
            writer.writerow([row.get(f) for f in fields])
        else:
            writer.writerow([getattr(row, f, "") for f in fields])

    csv_text = stream.getvalue()
    headers = {"Content-Disposition": f'attachment; filename="admin_report_{type}.csv"'}
    return Response(content=csv_text, media_type="text/csv", headers=headers)
