"""
mcp/tools/__init__.py

Satu titik untuk mendaftarkan semua modul tool ke registry. Tambah tool
baru = buat file baru di folder ini dengan fungsi setup(), lalu import &
panggil di sini. Tidak ada bagian lain dari core yang perlu diubah.
"""

from __future__ import annotations

from core.logger import get_logger
from mcp.tools import (
    currency,
    news,
    telegram_tool,
    translate,
    weather,
    web_search,
    wiki,
    youtube_play_music,
    youtube_play_video,
    youtube_search_music,
    youtube_search_video,
)

logger = get_logger("mcp.tools")

_ALL_MODULES = [
    web_search,
    weather,
    news,
    wiki,
    currency,
    translate,
    youtube_search_music,
    youtube_search_video,
    youtube_play_music,
    youtube_play_video,
    telegram_tool,
]


def setup_all_tools() -> None:
    for module in _ALL_MODULES:
        module.setup()
    logger.info("Semua modul tool terdaftar (%d modul)", len(_ALL_MODULES))
