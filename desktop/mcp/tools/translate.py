"""
mcp/tools/translate.py

translate.text — pakai endpoint kompatibel LibreTranslate (endpoint &
API key bisa diatur lewat dashboard, default ke instance publik). Instance
publik biasanya dibatasi rate limit; untuk pemakaian rutin disarankan
self-host LibreTranslate sendiri atau pakai instance berbayar, lalu ganti
endpoint-nya di Settings.
"""

from __future__ import annotations

from core.config import config
from mcp.server import registry
from mcp.tools._http import client


async def translate_text(arguments: dict) -> dict:
    text = (arguments.get("text") or "").strip()
    if not text:
        raise ValueError("Parameter 'text' tidak boleh kosong")
    if len(text) > 2000:
        raise ValueError("Parameter 'text' terlalu panjang (maksimal 2000 karakter)")

    target_lang = (arguments.get("target_lang") or "").strip().lower()
    if len(target_lang) != 2:
        raise ValueError("Parameter 'target_lang' harus kode ISO 639-1, 2 huruf")

    source_lang = (arguments.get("source_lang") or "auto").strip().lower()

    cfg = config.get("api_keys", "translate", default={}) or {}
    endpoint = (cfg.get("endpoint") or "https://libretranslate.com").rstrip("/")
    api_key = cfg.get("api_key", "")

    payload = {"q": text, "source": source_lang, "target": target_lang, "format": "text"}
    if api_key:
        payload["api_key"] = api_key

    async with client() as http:
        resp = await http.post(f"{endpoint}/translate", json=payload)
    if resp.status_code == 403:
        raise ValueError("Endpoint translate menolak permintaan (kemungkinan butuh API key, isi di Settings)")
    resp.raise_for_status()
    data = resp.json()

    return {"translated_text": data.get("translatedText"), "source_lang": source_lang, "target_lang": target_lang}


def setup() -> None:
    registry.register(
        name="translate.text",
        description="Menerjemahkan teks ke bahasa lain. Gunakan saat user minta terjemahan kata/kalimat.",
        input_schema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "minLength": 1, "maxLength": 2000, "description": "Teks yang diterjemahkan"},
                "target_lang": {"type": "string", "description": "Kode bahasa tujuan ISO 639-1, contoh 'en'"},
                "source_lang": {"type": "string", "default": "auto", "description": "Kode bahasa asal, 'auto' untuk deteksi otomatis"},
            },
            "required": ["text", "target_lang"],
        },
        handler=translate_text,
        category="info_search",
    )
