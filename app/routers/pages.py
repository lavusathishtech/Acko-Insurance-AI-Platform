from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["pages"])

templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")


@router.get("/customer-dashboard", response_class=HTMLResponse)
async def customer_dashboard_page(request: Request):
    return templates.TemplateResponse(request=request, name="customer_dashboard.html")


@router.get("/dashboard", response_class=HTMLResponse)
async def manager_dashboard_page(request: Request):
    return templates.TemplateResponse(request=request, name="manager_dashboard.html")
