"""
webapp/mcp_app.py

App FastAPI TERPISAH dari dashboard, sengaja minim — hanya endpoint
WebSocket MCP. Ini yang dibuka ke jaringan luar (mcp_host, biasanya
0.0.0.0) supaya backend cloud XiaoZhi bisa konek. Dashboard (settings UI)
TIDAK ada di app ini, jadi walau port ini diekspos ke internet, tidak ada
permukaan untuk mengubah setting tanpa otentikasi.

Catatan: dashboard (webapp/dashboard_app.py) sendiri sekarang juga default
dengar di 0.0.0.0 (bukan localhost-only) supaya bisa diakses dari device
lain di LAN. Beda dengan app ini, dashboard TIDAK punya autentikasi sama
sekali — jangan port-forward dashboard_port ke internet publik.
"""

from __future__ import annotations

import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.responses import JSONResponse

from core.config import config
from core.logger import get_logger
from core.state import state
from mcp.dispatcher import handle_rpc, server_info

logger = get_logger("webapp.mcp")


def create_mcp_app() -> FastAPI:
    app = FastAPI(title="xiaozhi-mcp-console (MCP endpoint)", docs_url=None, redoc_url=None)

    @app.get("/")
    async def health():
        return JSONResponse({
            "service": server_info()["name"],
            "version": server_info()["version"],
            "status": "ok",
        })

    ws_path = config.get("network", "mcp_ws_path", default="/mcp")

    @app.websocket(ws_path)
    async def mcp_endpoint(websocket: WebSocket):
        await websocket.accept()
        remote = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown"
        conn_id = state.register_connection(remote)
        logger.info("MCP client terhubung: %s (conn_id=%s)", remote, conn_id)
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps(
                        {"jsonrpc": "2.0", "id": None, "error": {"message": "Invalid JSON"}}
                    ))
                    continue

                state.touch_connection(conn_id, message.get("method", ""))
                response = await handle_rpc(message)
                if response is not None:
                    await websocket.send_text(json.dumps(response, ensure_ascii=False))
        except WebSocketDisconnect:
            logger.info("MCP client terputus: %s (conn_id=%s)", remote, conn_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Koneksi MCP error (conn_id=%s): %s", conn_id, exc)
        finally:
            state.drop_connection(conn_id)

    return app
