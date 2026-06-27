"""
webapp/routes_api.py — REST API untuk dashboard.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.config import config
from core.logger import ring_handler
from core.state import state
from integrations import telegram_bot, xiaozhi_client
from mcp.server import registry
from mcp.tools._browser import find_brave_executable

router = APIRouter(prefix="/api")


def _format_uptime(seconds: float) -> str:
    s = int(seconds)
    days, s = divmod(s, 86400)
    hours, s = divmod(s, 3600)
    minutes, s = divmod(s, 60)
    parts = []
    if days:        parts.append(f"{days}h")
    if hours or days: parts.append(f"{hours}j")
    parts.append(f"{minutes}m")
    parts.append(f"{s}d")
    return " ".join(parts)


# ─── Status ──────────────────────────────────────────────────────────────────

@router.get("/status")
async def get_status():
    enabled_count = sum(1 for t in registry.all_tools() if registry.is_enabled(t.name))
    return {
        "uptime_seconds": state.uptime_seconds(),
        "uptime_human": _format_uptime(state.uptime_seconds()),
        "xiaozhi": state.xiaozhi.to_dict(),
        "inbound_connections": state.list_inbound_connections(),
        "tool_call_count": state.tool_call_count,
        "tool_error_count": state.tool_error_count,
        "tools_enabled_count": enabled_count,
        "recent_calls": list(state.call_history)[-50:],
        "network": config.get("network", default={}),
        "restart_required": state.restart_requested,
    }


# ─── XiaoZhi connection ───────────────────────────────────────────────────────

@router.get("/xiaozhi/status")
async def get_xiaozhi_status():
    return state.xiaozhi.to_dict()


@router.post("/xiaozhi/reconnect")
async def reconnect_xiaozhi():
    xiaozhi_client.reconnect()
    return {"ok": True, "message": "Force reconnect dikirim ke client"}


@router.post("/xiaozhi/disable")
async def disable_xiaozhi():
    config.set_path(("xiaozhi", "enabled"), False)
    await xiaozhi_client.stop()
    state.xiaozhi.status = "disconnected"
    state.xiaozhi.last_error = "Dinonaktifkan manual dari dashboard"
    return {"ok": True}


@router.post("/xiaozhi/enable")
async def enable_xiaozhi():
    config.set_path(("xiaozhi", "enabled"), True)
    state.xiaozhi.last_error = ""
    await xiaozhi_client.start()
    return {"ok": True}


# ─── Config ───────────────────────────────────────────────────────────────────

_NETWORK_FIELDS = {
    "dashboard_host", "dashboard_port",
    "inbound_mcp_enabled", "inbound_mcp_host", "inbound_mcp_port",
    "inbound_mcp_ws_path", "use_tls", "tls_cert_path", "tls_key_path",
}


@router.get("/config")
async def get_config():
    return config.all_masked()


@router.post("/config")
async def update_config(payload: dict):
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Body harus berupa JSON object")

    network_changed = bool(_NETWORK_FIELDS.intersection((payload.get("network") or {}).keys()))
    xiaozhi_section = payload.get("xiaozhi") or {}

    config.update(payload)

    if network_changed:
        state.restart_requested = True

    # Perubahan config XiaoZhi → bersihkan error lama dan reconnect
    if xiaozhi_section:
        token = config.get("xiaozhi", "token", default="")
        if xiaozhi_section.get("enabled") is False:
            await xiaozhi_client.stop()
            state.xiaozhi.status = "disconnected"
            state.xiaozhi.last_error = "Dinonaktifkan di Settings"
        elif token:
            # Ada token baru atau perubahan URL → update wss_url tampil segera
            base = config.get("xiaozhi", "wss_base_url", default="")
            sep = "&" if "?" in base else "?"
            safe_url = f"{base.rstrip('/')}/{sep}token={token[:6]}...{token[-6:]}"
            state.xiaozhi.wss_url = safe_url
            state.xiaozhi.last_error = ""
            state.xiaozhi.status = "connecting"
            xiaozhi_client.reconnect()
        else:
            state.xiaozhi.last_error = "Token belum diatur (Settings → XiaoZhi Connection)"

    # Toggle Telegram bot
    telegram_section = payload.get("telegram") or {}
    if "bot_enabled" in telegram_section:
        if telegram_section["bot_enabled"]:
            telegram_bot.start_background_task()
        else:
            telegram_bot.stop_background_task()

    return {"ok": True, "config": config.all_masked(), "restart_required": state.restart_requested}


# ─── Network restart ──────────────────────────────────────────────────────────

@router.post("/restart")
async def restart_listeners():
    state.restart_requested = True
    if state.dashboard_server is not None:
        state.dashboard_server.should_exit = True
    if state.mcp_server is not None:
        state.mcp_server.should_exit = True
    return {"ok": True, "message": "Restart diminta"}


# ─── Browser (Brave) ───────────────────────────────────────────────────────────

@router.get("/browser/detect")
async def detect_browser():
    """Dipakai tombol 'Test deteksi' di Settings — cek apakah brave.exe
    ketemu lewat config manual / lokasi umum / PATH, tanpa benar-benar
    membuka jendela browser."""
    try:
        path = find_brave_executable()
        return {"ok": True, "path": path}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc))


# ─── Tools ────────────────────────────────────────────────────────────────────

@router.get("/tools")
async def list_tools():
    return registry.list_tools_with_status()


class ToolToggle(BaseModel):
    name: str
    enabled: bool


@router.post("/tools/toggle")
async def toggle_tool(payload: ToolToggle):
    if registry.get(payload.name) is None:
        raise HTTPException(status_code=404, detail=f"Tool '{payload.name}' tidak ditemukan")
    config.set_path(("tools_enabled", payload.name), payload.enabled)
    return {"ok": True, "name": payload.name, "enabled": payload.enabled}


class ToolTest(BaseModel):
    name: str
    arguments: dict = {}


@router.post("/tools/test")
async def test_tool(payload: ToolTest):
    if registry.get(payload.name) is None:
        raise HTTPException(status_code=404, detail=f"Tool '{payload.name}' tidak ditemukan")
    try:
        result = await registry.call(payload.name, payload.arguments)
        return {"ok": True, "result": result}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc))


# ─── Logs ─────────────────────────────────────────────────────────────────────

@router.get("/logs")
async def get_logs(level: str | None = None, limit: int = 200):
    return ring_handler.get_logs(level=level, limit=limit)
