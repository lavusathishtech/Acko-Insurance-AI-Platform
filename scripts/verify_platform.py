"""Smoke test for ACKO platform APIs. Run: python scripts/verify_platform.py"""
from __future__ import annotations

import json
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def get(path: str):
    with urllib.request.urlopen(f"{BASE}{path}") as r:
        return json.loads(r.read().decode())


def post(path: str, body: dict):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def main():
    health = get("/health")
    assert health.get("status") == "ok", health
    login = post("/api/auth/login", {"email": "customer@acko.demo", "password": "customer123"})
    assert "access_token" in login
    premium = post(
        "/predict-premium",
        {
            "vehicle_type": "Car",
            "model": "Honda Amaze",
            "year": 2022,
            "fuel_type": "Petrol",
            "city": "Bengaluru",
            "idv": 450000,
            "ncb": 20,
        },
    )
    assert "predicted_premium" in premium
    chat = post("/chatbot", {"message": "What is NCB?", "lang": "en"})
    assert "reply" in chat
    dash = get("/dashboard-data")
    assert "kpis" in dash
    print("All smoke checks passed.")


if __name__ == "__main__":
    main()
