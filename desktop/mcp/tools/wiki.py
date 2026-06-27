"""
mcp/tools/wiki.py

wiki.lookup — mencari ringkasan artikel Wikipedia.

Strategi dua endpoint (fallback):
  1. REST summary API  (https://LANG.wikipedia.org/api/rest_v1/page/summary/TERM)
     → response cepat, ringkasan siap pakai
  2. MediaWiki Action API  (https://LANG.wikipedia.org/w/api.php?action=query&...)
     → fallback kalau REST API 403/gagal; lebih kompatibel dengan berbagai
       konfigurasi jaringan dan proxy

Wikimedia User-Agent Policy:
  Wajib berbentuk "AppName/version (contact)" — string generik (mis.
  "python-httpx") diblokir 403. Referensi:
  https://www.mediawiki.org/wiki/API:REST_API#Terms_and_conditions
"""

from __future__ import annotations

import urllib.parse

from mcp.server import registry
from mcp.tools._http import client

_WIKI_HEADERS = {
    "User-Agent": "xiaozhi-mcp-console/1.1 (https://github.com/xiaozhi-mcp-console; mcp-bot)",
    "Accept": "application/json",
}


async def _via_rest_api(lang: str, term: str) -> dict | None:
    """Endpoint utama: REST summary API. Cepat dan ringkasan sudah bersih."""
    url = (
        f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/"
        f"{urllib.parse.quote(term, safe='')}"
    )
    async with client(headers=_WIKI_HEADERS) as http:
        resp = await http.get(url, follow_redirects=True)

    if resp.status_code == 404:
        return None  # artikel tidak ada
    if resp.status_code == 403:
        return False  # endpoint diblokir → coba fallback
    resp.raise_for_status()
    data = resp.json()
    return {
        "title": data.get("title"),
        "summary": data.get("extract"),
        "url": data.get("content_urls", {}).get("desktop", {}).get("page"),
    }


async def _via_action_api(lang: str, term: str) -> dict | None:
    """Fallback: MediaWiki Action API.
    Lebih kompatibel — berjalan bahkan di host yang memblokir endpoint
    REST modern, karena action API sudah ada sejak lama dan jarang difilter.
    """
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": term,
        "prop": "extracts|info",
        "exintro": "1",
        "explaintext": "1",
        "exsentences": "5",     # ambil 5 kalimat pertama sebagai ringkasan
        "inprop": "url",
        "redirects": "1",
        "format": "json",
        "formatversion": "2",
    }
    async with client(headers=_WIKI_HEADERS) as http:
        resp = await http.get(url, params=params, follow_redirects=True)

    if resp.status_code in (403, 404):
        return None
    resp.raise_for_status()
    data = resp.json()

    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return None
    page = pages[0]
    if page.get("missing"):
        return None

    title = page.get("title", term)
    page_url = f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
    extract = (page.get("extract") or "").strip()
    return {
        "title": title,
        "summary": extract if extract else None,
        "url": page_url,
    }


async def lookup(arguments: dict) -> dict:
    term = (arguments.get("term") or "").strip()
    if not term:
        raise ValueError("Parameter 'term' tidak boleh kosong")
    if len(term) > 150:
        raise ValueError("Parameter 'term' terlalu panjang (maksimal 150 karakter)")

    language = (arguments.get("language") or "id").strip().lower()
    if len(language) != 2:
        raise ValueError("Parameter 'language' harus kode ISO 639-1, 2 huruf (contoh: 'id', 'en')")

    # Coba REST API dulu
    result = await _via_rest_api(language, term)

    if result is None:
        raise ValueError(f"Artikel '{term}' tidak ditemukan di Wikipedia bahasa '{language}'")

    if result is False:
        # REST API diblokir (403) → fallback ke Action API
        result = await _via_action_api(language, term)
        if result is None:
            raise ValueError(
                f"Artikel '{term}' tidak ditemukan di Wikipedia bahasa '{language}'"
            )

    return result


def setup() -> None:
    registry.register(
        name="wiki.lookup",
        description=(
            "Mencari ringkasan artikel Wikipedia berdasarkan istilah/judul. "
            "Gunakan untuk pertanyaan faktual umum (orang, tempat, konsep, sejarah)."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "term": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 150,
                    "description": "Istilah atau judul artikel yang dicari",
                },
                "language": {
                    "type": "string",
                    "default": "id",
                    "description": "Kode bahasa ISO 639-1, 2 huruf (contoh: 'id', 'en')",
                },
            },
            "required": ["term"],
        },
        handler=lookup,
        category="info_search",
    )
