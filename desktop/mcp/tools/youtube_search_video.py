"""
mcp/tools/youtube_search_video.py

youtube.search_video — pakai YouTube Data API v3, butuh API key dari dashboard.

Memakai helper `_search()` dari youtube_search_music.py supaya logic
pemanggilan API YouTube tidak terduplikasi antar tool pencarian yang serupa.
"""

from __future__ import annotations

from mcp.server import registry
from mcp.tools.youtube_search_music import _search


async def search_video(arguments: dict) -> dict:
    query = (arguments.get("query") or "").strip()
    if not query:
        raise ValueError("Parameter 'query' tidak boleh kosong")
    if len(query) > 150:
        raise ValueError("Parameter 'query' terlalu panjang (maksimal 150 karakter)")
    max_results = arguments.get("max_results", 5)
    if not isinstance(max_results, int) or not (1 <= max_results <= 10):
        raise ValueError("Parameter 'max_results' harus angka 1-10")
    return await _search(query, max_results, video_category_id=None)


def setup() -> None:
    registry.register(
        name="youtube.search_video",
        description="Mencari video (bukan khusus musik) di YouTube berdasarkan kata kunci.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 1, "maxLength": 150, "description": "Kata kunci pencarian video"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
            },
            "required": ["query"],
        },
        handler=search_video,
        category="media",
    )
