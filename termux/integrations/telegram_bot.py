"""
integrations/telegram_bot.py

Bot Telegram opsional yang jalan di background (asyncio task), DI LUAR
tool telegram.send_message. Dua fungsi:
1. Kirim notifikasi otomatis saat server start (kalau notify_on_start aktif).
2. Long-poll getUpdates dan balas command sederhana: /status, /help —
   supaya Anda bisa cek status server cuma dengan chat ke bot dari HP,
   tanpa harus buka dashboard.

Diaktifkan/dimatikan lewat dashboard > Settings > Telegram > "Aktifkan bot".
Berhenti otomatis kalau bot_enabled dimatikan (dicek tiap iterasi loop).
"""

from __future__ import annotations

import asyncio

from core.config import config
from core.logger import get_logger
from core.state import state
from integrations import telegram_api

logger = get_logger("integrations.telegram_bot")

_task: asyncio.Task | None = None


def _format_uptime(seconds: float) -> str:
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f"{days}h")
    if hours:
        parts.append(f"{hours}j")
    parts.append(f"{minutes}m")
    return " ".join(parts)


async def _status_text() -> str:
    conns = state.list_connections()
    return (
        f"🟢 xiaozhi-mcp-console aktif\n"
        f"Uptime: {_format_uptime(state.uptime_seconds())}\n"
        f"Koneksi MCP aktif: {len(conns)}\n"
        f"Total tool calls: {state.tool_call_count} "
        f"(error: {state.tool_error_count})"
    )


async def _handle_command(text: str, chat_id: str) -> None:
    text = text.strip().split()[0].lower() if text.strip() else ""
    if text in ("/status", "/start"):
        await telegram_api.send_message(await _status_text(), chat_id)
    elif text == "/help":
        await telegram_api.send_message(
            "Command tersedia:\n/status - lihat status server\n/help - bantuan ini",
            chat_id,
        )


async def notify_startup() -> None:
    if not config.get("telegram", "notify_on_start", default=False):
        return
    if not telegram_api.is_configured():
        return
    try:
        await telegram_api.send_message("🚀 xiaozhi-mcp-console baru saja start.")
    except ValueError as exc:
        logger.warning("Gagal mengirim notifikasi startup Telegram: %s", exc)


async def _poll_loop() -> None:
    offset: int | None = None
    logger.info("Telegram bot poller dimulai")
    while True:
        if not config.get("telegram", "bot_enabled", default=False):
            logger.info("Telegram bot dinonaktifkan, poller berhenti")
            return
        if not telegram_api.is_configured():
            await asyncio.sleep(5)
            continue
        try:
            updates = await telegram_api.get_updates(offset, timeout=20)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Telegram getUpdates gagal: %s", exc)
            await asyncio.sleep(5)
            continue

        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message") or {}
            text = message.get("text", "")
            chat_id = str((message.get("chat") or {}).get("id", ""))
            if text.startswith("/") and chat_id:
                try:
                    await _handle_command(text, chat_id)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Gagal membalas command Telegram: %s", exc)

        if not updates:
            await asyncio.sleep(1)


def start_background_task() -> None:
    global _task
    if _task is not None and not _task.done():
        return
    if not config.get("telegram", "bot_enabled", default=False):
        return
    _task = asyncio.create_task(_poll_loop())
    logger.info("Telegram bot background task disiapkan")


def stop_background_task() -> None:
    global _task
    if _task is not None and not _task.done():
        _task.cancel()
    _task = None
