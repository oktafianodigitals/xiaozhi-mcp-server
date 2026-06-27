"""
webapp/dashboard_app.py

App FastAPI untuk dashboard (UI + REST API manajemen). Dipisah dari
webapp/mcp_app.py karena keduanya dibind ke host:port yang berbeda — lihat
penjelasan di mcp_app.py dan README bagian "Arsitektur Jaringan".
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from webapp import routes_api, routes_pages

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_dashboard_app() -> FastAPI:
    app = FastAPI(title="xiaozhi-mcp-console (dashboard)", docs_url="/api/docs", redoc_url=None)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.include_router(routes_pages.router)
    app.include_router(routes_api.router)
    return app
