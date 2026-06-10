from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import FRONTEND_DIR, IMAGES_DIR, REACT_DIST, SERVE_REACT_UI
from app.routers import admin, auth, chatbot, claims, customer, dashboard, notifications, pages, policies, premium

app = FastAPI(title="ACKO Insurance AI Platform", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(premium.router)
app.include_router(claims.router)
app.include_router(chatbot.router)
app.include_router(dashboard.router)
app.include_router(admin.router)
app.include_router(customer.router)
app.include_router(policies.router)
app.include_router(notifications.router)
app.include_router(pages.router)

app.mount("/images", StaticFiles(directory=str(IMAGES_DIR)), name="images")


@app.get("/health")
async def health():
    db_ok = False
    try:
        from app.database import db_available

        db_ok = db_available()
    except Exception:
        db_ok = False
    return {"status": "ok", "database": db_ok}


def _use_react_ui() -> bool:
    return SERVE_REACT_UI and REACT_DIST.exists()


if _use_react_ui():
    app.mount("/assets", StaticFiles(directory=str(REACT_DIST / "assets")), name="react-assets")

    @app.get("/", include_in_schema=False)
    async def react_home():
        return FileResponse(REACT_DIST / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def react_spa(full_path: str):
        candidate = REACT_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(REACT_DIST / "index.html")
else:
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    # Serve legacy website under '/oldsite'
    app.mount("/oldsite", StaticFiles(directory="deployment/website"), name="oldsite")
