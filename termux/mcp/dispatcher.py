"""
mcp/dispatcher.py

Implementasi method JSON-RPC 2.0 inti MCP: initialize, tools/list, tools/call.
Dipakai oleh endpoint WebSocket /mcp di webapp/mcp_app.py. Dipisah dari
endpoint-nya sendiri supaya logic ini bisa dites tanpa perlu koneksi
WebSocket sungguhan (lihat tests/test_dispatcher.py).
"""

from __future__ import annotations

import json

from core.config import config
from core.logger import get_logger
from mcp.server import registry

logger = get_logger("mcp.dispatcher")

PROTOCOL_VERSION = "2024-11-05"


def server_info() -> dict:
    return {
        "name": config.get("meta", "server_name", default="xiaozhi-mcp-console"),
        "version": config.get("meta", "version", default="1.0.0"),
    }


async def handle_rpc(message: dict) -> dict | None:
    method = message.get("method", "")
    msg_id = message.get("id")
    params = message.get("params", {}) or {}

    # Konsisten dengan perilaku firmware Arah 1: method "notifications/*"
    # tidak dibalas sama sekali.
    if method.startswith("notifications"):
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": msg_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": server_info(),
            },
        }

    if method == "tools/list":
        return {
            "jsonrpc": "2.0", "id": msg_id,
            "result": {"tools": registry.list_tools()},
        }

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments", {}) or {}
        try:
            result = await registry.call(name, arguments)
            return {
                "jsonrpc": "2.0", "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                    "isError": False,
                },
            }
        except Exception as exc:  # noqa: BLE001 — boundary tool eksternal
            logger.warning("tools/call '%s' gagal: %s", name, exc)
            # Konsisten dengan Arah 1: hanya field "message", tanpa "code".
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"message": str(exc)}}

    return {
        "jsonrpc": "2.0", "id": msg_id,
        "error": {"message": f"Method not implemented: {method}"},
    }
