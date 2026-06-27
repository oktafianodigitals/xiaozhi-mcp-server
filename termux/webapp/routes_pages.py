"""webapp/routes_pages.py — route halaman HTML."""
from __future__ import annotations
from fastapi import APIRouter, Request
from core.config import config
from core.defaults import DEFAULT_CONFIG
from core.state import state
from webapp.templating import templates

router = APIRouter()

def _ctx(request, active_page):
    return {
        "active_page": active_page,
        "app_version": DEFAULT_CONFIG["meta"]["version"],
    }

@router.get("/")
async def page_status(request: Request):
    return templates.TemplateResponse(request, "index.html", _ctx(request, "status"))

@router.get("/settings")
async def page_settings(request: Request):
    ctx = _ctx(request, "settings")
    ctx["cfg"] = config.all_masked()
    ctx["restart_required"] = state.restart_requested
    return templates.TemplateResponse(request, "settings.html", ctx)

@router.get("/tools")
async def page_tools(request: Request):
    return templates.TemplateResponse(request, "tools.html", _ctx(request, "tools"))

@router.get("/logs")
async def page_logs(request: Request):
    return templates.TemplateResponse(request, "logs.html", _ctx(request, "logs"))
