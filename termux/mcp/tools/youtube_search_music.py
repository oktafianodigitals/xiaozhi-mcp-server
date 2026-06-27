"""
mcp/tools/youtube_search_music.py

youtube.search_music — pakai YouTube Data API v3, butuh API key dari dashboard.

Helper `_search()` di sini dipakai bersama oleh youtube_search_video.py
(diimpor dari modul ini) supaya logic pemanggilan API YouTube tidak
terduplikasi antar tool yang serupa.
"""

from __future__ import annotations

from core.config import config
from mcp.server import registry
from mcp.tools._http import client

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def _require_api_key() -> str:
    api_key = config.get("api_keys", "youtube", "api_key", default="")
    if not api_key:
        raise ValueError(
            "API key YouTube belum diatur. Buka dashboard > Settings > API Keys, "
            "isi YouTube Data API v3 key, lalu simpan."
        )
    return api_key


async def _search(query: str, max_results: int, video_category_id: str | None) -> dict:
    api_key = _require_api_key()
    params = {
        "part": "snippet", "q": query, "type": "video",
        "maxResults": max_results, "key": api_key,
    }
    if video_category_id:
        params["videoCategoryId"] = video_category_id

    async with client() as http:
        resp = await http.get(YOUTUBE_SEARCH_URL, params=params)
    if resp.status_code == 403:
        raise ValueError("API key YouTube ditolak (kuota habis atau key tidak valid)")
    resp.raise_for_status()
    items = resp.json().get("items", [])

    return {"results": [
        {
            "title": it["snippet"]["title"],
            "channel": it["snippet"]["channelTitle"],
            "video_id": it["id"]["videoId"],
            "url": f"https://www.youtube.com/watch?v={it['id']['videoId']}",
        }
        for it in items
    ]}


async def search_music(arguments: dict) -> dict:
    query = (arguments.get("query") or "").strip()
    if not query:
        raise ValueError("Parameter 'query' tidak boleh kosong")
    if len(query) > 150:
        raise ValueError("Parameter 'query' terlalu panjang (maksimal 150 karakter)")
    max_results = arguments.get("max_results", 5)
    if not isinstance(max_results, int) or not (1 <= max_results <= 10):
        raise ValueError("Parameter 'max_results' harus angka 1-10")
    return await _search(query, max_results, video_category_id="10")  # 10 = Music


def setup() -> None:
    registry.register(
        name="youtube.search_music",
        description=(
            "Mencari dan memutar lagu ASLI dari YouTube berdasarkan judul/penyanyi. "
            "WAJIB gunakan tool ini untuk permintaan musik apa pun, bukan database musik "
            "internal, karena ini memberi hasil pencarian real-time dari katalog YouTube."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 1, "maxLength": 150, "description": "Judul lagu atau nama artis"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
            },
            "required": ["query"],
        },
        handler=search_music,
        category="media",
    )
