"""
integrations/telegram_api.py

Wrapper kecil untuk Telegram Bot API, dipakai bersama oleh:
- mcp/tools/telegram_tool.py (tool telegram.send_message, dipanggil LLM)
- integrations/telegram_bot.py (notifikasi status & command /status, /help)

Sengaja dipisah dari kedua pemakainya supaya logic HTTP-nya satu tempat.
"""

from __future__ import annotations

from core.config import config
from mcp.tools._http import client


def is_configured() -> bool:
    return bool(config.get("telegram", "bot_token", default=""))


async def send_message(text: str, chat_id: str | None = None) -> dict:
    bot_token = config.get("telegram", "bot_token", default="")
    if not bot_token:
        raise ValueError(
            "Bot token Telegram belum diatur. Buka dashboard > Settings > "
            "Telegram, isi bot token (dari @BotFather), lalu simpan."
        )

    target_chat_id = chat_id or config.get("telegram", "default_chat_id", default="")
    if not target_chat_id:
        raise ValueError(
            "Tidak ada 'chat_id' yang diberikan dan default_chat_id juga belum "
            "diatur di dashboard > Settings > Telegram."
        )

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    async with client() as http:
        resp = await http.post(url, json={"chat_id": target_chat_id, "text": text})
    data = resp.json()
    if not data.get("ok"):
        raise ValueError(f"Telegram menolak pesan: {data.get('description', 'unknown error')}")
    return {"status": "sent", "chat_id": target_chat_id}


async def get_updates(offset: int | None, timeout: int = 25) -> list[dict]:
    bot_token = config.get("telegram", "bot_token", default="")
    if not bot_token:
        return []
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    async with client(timeout=timeout + 10) as http:
        resp = await http.get(url, params=params)
    data = resp.json()
    if not data.get("ok"):
        return []
    return data.get("result", [])
