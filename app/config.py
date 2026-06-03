from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
REACT_DIST = BASE_DIR / "client-app" / "dist"
# Default: previous ACKO blue SPA in frontend/. Set SERVE_REACT_UI=true for InsureX React build.
SERVE_REACT_UI = os.getenv("SERVE_REACT_UI", "false").lower() in {"1", "true", "yes"}
IMAGES_DIR = BASE_DIR / "images"
DOCS_DIR = BASE_DIR / "docs"
POLICIES_DIR = BASE_DIR / "generated_policies"

JWT_SECRET = os.getenv("JWT_SECRET", "acko-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

ENABLE_GEMINI_CHAT = os.getenv("ENABLE_GEMINI_CHAT", "true").lower() in {"1", "true", "yes"}
ENABLE_GEMINI_DAMAGE = os.getenv("ENABLE_GEMINI_DAMAGE", "true").lower() in {"1", "true", "yes"}
ENABLE_TENSORFLOW_DAMAGE = os.getenv("ENABLE_TENSORFLOW_DAMAGE", "false").lower() in {"1", "true", "yes"}
