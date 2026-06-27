"""
mcp/tools/web_search.py

web.search — pakai Brave Search API. Butuh API key yang diisi lewat
dashboard (Settings > API Keys). Brave dipilih karena punya free tier untuk
penggunaan personal dan tidak butuh kartu kredit untuk mulai.
"""

from __future__ import annotations

from core.config import config
from mcp.server import registry
from mcp.tools._http import client

BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"


async def search(arguments: dict) -> dict:
    query = (arguments.get("query") or "").strip()
    if not query:
        raise ValueError("Parameter 'query' tidak boleh kosong")
    if len(query) > 200:
        raise ValueError("Parameter 'query' terlalu panjang (maksimal 200 karakter)")

    max_results = arguments.get("max_results", 5)
    if not isinstance(max_results, int) or not (1 <= max_results <= 10):
        raise ValueError("Parameter 'max_results' harus angka 1-10")

    api_key = config.get("api_keys", "web_search", "api_key", default="")
    if not api_key:
        raise ValueError(
            "API key web search belum diatur. Buka dashboard > Settings > "
            "API Keys, isi Brave Search API key, lalu simpan."
        )

    async with client(headers={"X-Subscription-Token": api_key, "Accept": "application/json"}) as http:
        resp = await http.get(BRAVE_URL, params={"q": query, "count": max_results})
    if resp.status_code == 401:
        raise ValueError("API key web search tidak valid (ditolak oleh Brave Search)")
    resp.raise_for_status()
    items = resp.json().get("web", {}).get("results", [])

    return {"results": [
        {"title": it.get("title"), "url": it.get("url"), "snippet": it.get("description")}
        for it in items[:max_results]
    ]}


def setup() -> None:
    registry.register(
        name="web.search",
        description=(
            "Mencari informasi terkini di internet. Gunakan untuk pertanyaan "
            "tentang berita terbaru, fakta yang mungkin berubah, atau apa pun "
            "yang tidak bisa dijawab dari pengetahuan umum."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 1, "maxLength": 200,
                           "description": "Kata kunci pencarian"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5,
                                 "description": "Jumlah hasil yang dikembalikan"},
            },
            "required": ["query"],
        },
        handler=search,
        category="info_search",
    )
