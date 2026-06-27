"""
mcp/tools/youtube_play_music.py

youtube.play_music — membuka Brave browser di mesin lokal dan memutar
video YouTube berdasarkan video_id. video_id WAJIB berasal dari hasil
youtube.search_music supaya LLM tidak menebak ID secara langsung
(lihat catatan di §6.2 dokumen spesifikasi).

Pemutaran dilakukan dengan men-spawn proses Brave baru yang mengarah ke
URL watch?v=<id> — bukan lewat API YouTube apa pun. Lihat mcp/tools/_browser.py
untuk strategi deteksi lokasi brave.exe.
"""

from __future__ import annotations

import re

from mcp.server import registry
from mcp.tools._browser import open_url_in_brave

VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")


async def play_music(arguments: dict) -> dict:
    video_id = arguments.get("video_id", "")
    if not VIDEO_ID_PATTERN.match(video_id):
        raise ValueError(
            "Parameter 'video_id' tidak valid. Harus 11 karakter dari hasil "
            "youtube.search_music — jangan menebak ID secara langsung."
        )
    url = f"https://www.youtube.com/watch?v={video_id}"
    brave_path = open_url_in_brave(url)
    return {"status": "playing", "video_id": video_id, "url": url, "browser_path": brave_path}


def setup() -> None:
    registry.register(
        name="youtube.play_music",
        description=(
            "Membuka Brave browser dan memutar lagu YouTube berdasarkan video_id "
            "hasil youtube.search_music. Panggil tool ini SETELAH search, jangan "
            "menebak video_id sendiri."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "video_id": {"type": "string", "pattern": "^[A-Za-z0-9_-]{11}$",
                              "description": "ID video YouTube, dari hasil search"},
            },
            "required": ["video_id"],
        },
        handler=play_music,
        category="media",
    )

