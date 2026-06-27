"""
mcp/tools/news.py

news.search — pakai NewsAPI.org. Butuh API key dari dashboard.
"""

from __future__ import annotations

from core.config import config
from mcp.server import registry
from mcp.tools._http import client

NEWSAPI_URL = "https://newsapi.org/v2/everything"


async def search(arguments: dict) -> dict:
    topic = (arguments.get("topic") or "").strip()
    if not topic:
        raise ValueError("Parameter 'topic' tidak boleh kosong")
    if len(topic) > 100:
        raise ValueError("Parameter 'topic' terlalu panjang (maksimal 100 karakter)")

    language = (arguments.get("language") or "id").strip().lower()
    if len(language) != 2:
        raise ValueError("Parameter 'language' harus kode ISO 639-1, 2 huruf")

    max_results = arguments.get("max_results", 5)
    if not isinstance(max_results, int) or not (1 <= max_results <= 10):
        raise ValueError("Parameter 'max_results' harus angka 1-10")

    api_key = config.get("api_keys", "news", "api_key", default="")
    if not api_key:
        raise ValueError(
            "API key News belum diatur. Buka dashboard > Settings > API Keys, "
            "isi NewsAPI.org key, lalu simpan."
        )

    async with client() as http:
        resp = await http.get(NEWSAPI_URL, params={
            "q": topic, "language": language, "pageSize": max_results,
            "sortBy": "publishedAt", "apiKey": api_key,
        })
    if resp.status_code == 401:
        raise ValueError("API key News tidak valid (ditolak oleh NewsAPI.org)")
    resp.raise_for_status()
    articles = resp.json().get("articles", [])

    return {"results": [
        {
            "title": a.get("title"), "source": (a.get("source") or {}).get("name"),
            "published_at": a.get("publishedAt"), "url": a.get("url"),
        }
        for a in articles[:max_results]
    ]}


def setup() -> None:
    registry.register(
        name="news.search",
        description="Mencari berita terbaru berdasarkan topik. Gunakan saat user minta berita atau perkembangan terkini.",
        input_schema={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "minLength": 1, "maxLength": 100, "description": "Topik berita"},
                "language": {"type": "string", "default": "id", "description": "Kode bahasa ISO 639-1, 2 huruf"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
            },
            "required": ["topic"],
        },
        handler=search,
        category="info_search",
    )
