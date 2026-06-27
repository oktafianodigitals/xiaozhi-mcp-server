"""
mcp/tools/telegram_tool.py

telegram.send_message — mengirim pesan teks lewat bot Telegram yang
dikonfigurasi di dashboard (Settings > Telegram).
"""

from __future__ import annotations

from integrations import telegram_api
from mcp.server import registry


async def send_message(arguments: dict) -> dict:
    chat_id = str(arguments.get("chat_id") or "").strip() or None
    text = (arguments.get("text") or "").strip()
    if not text:
        raise ValueError("Parameter 'text' tidak boleh kosong")
    if len(text) > 4096:
        raise ValueError("Parameter 'text' terlalu panjang (maksimal 4096 karakter, limit Telegram API)")

    return await telegram_api.send_message(text, chat_id)


def setup() -> None:
    registry.register(
        name="telegram.send_message",
        description=(
            "Mengirim pesan teks lewat Telegram. Gunakan saat user secara eksplisit "
            "minta mengirim/notifikasi pesan ke Telegram. Jika 'chat_id' tidak "
            "disebutkan, akan dikirim ke chat default yang diatur di dashboard."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "chat_id": {"type": "string", "description": "ID chat/grup Telegram tujuan (opsional, pakai default jika kosong)"},
                "text": {"type": "string", "minLength": 1, "maxLength": 4096, "description": "Isi pesan"},
            },
            "required": ["text"],
        },
        handler=send_message,
        category="telegram",
    )
